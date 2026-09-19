# listing.json → 네이버 커머스API 상품 등록 실행
#
# 흐름:
#   1. products/<slug>/output/listing.json 로드
#   2. sanity check (필수값/역마진/목표마진) — 실패 시 등록하지 않고 status.json에 사유 기록
#   3. 이미지 업로드 API (POST /v1/product-images/upload) — 반환 URL 사용
#   4. 상품 등록 API  (POST /v2/products)
#   5. productNo/originProductNo를 status.json에 기록, status=registered
#
# 이미 status=registered 인 상품은 중복 등록을 막기 위해 스킵한다.
#
# 사용법:
#   python3 scripts/register_product.py products/<product-slug>

import argparse
import html
import json
import re
import mimetypes
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers
from detail_quality import audit_listing, repair_listing

ROOT = Path(__file__).resolve().parent.parent
STORE_CONFIG_PATH = ROOT / "config" / "store.json"
PRICING_CONFIG_PATH = ROOT / "config" / "pricing.json"
DETAIL_NOTICE_CONFIG_PATH = ROOT / "config" / "detail-notices.json"

IMAGE_UPLOAD_URL = f"{API_BASE}/v1/product-images/upload"
PRODUCT_URL = f"{API_BASE}/v2/products"
MAX_PRODUCT_IMAGES = 10

REQUIRED_FIELDS = ("name", "leafCategoryId", "salePrice", "stockQuantity", "detailContent", "images")
SEO_REQUIRED_FIELDS = ("brandName", "manufacturerName", "modelName", "originAreaInfo")
GENERIC_TITLE_LEADS = ("대용량", "고급", "인기", "추천", "최고", "할인", "특가", "정품", "무료배송")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_status(product_dir: Path, **updates):
    status_path = product_dir / "status.json"
    status = load_json(status_path) if status_path.exists() else {}
    clear_errors = updates.pop("_clear_errors", False)
    if clear_errors:
        status.pop("errors", None)
        status.pop("api_response", None)
    status.update(updates, updated_at=datetime.now().isoformat())
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def price_evidence_errors(product_dir: Path) -> list[str]:
    """사용자가 직접 재현할 수 있는 가격 근거가 없는 등록을 막는다."""
    path = product_dir / "output" / "price-research.json"
    if not path.exists():
        return ["가격 조사 기록 없음: output/price-research.json 필요"]
    try:
        research = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"가격 조사 기록을 읽을 수 없음: {exc}"]

    # pricing.md의 기록 항목은 가격 변경 근거를 나중에 재현하기 위한 최소 기록이다.
    # 가격표 이미지가 없는 경우에도 userImageCost에는 unavailable 상태와 사유를 남긴다.
    record_fields = (
        "userImageCost", "costcoOfficialCost", "adoptedCost", "competitors",
        "targetMarginCalculation", "minimumMarginApplied", "finalProductPrice",
        "finalCustomerDeliveryFee", "totalPaymentAmount", "expectedNetMargin",
        "calculatedAt", "decisionReason",
    )
    missing = [field for field in record_fields if field not in research]
    if missing:
        return ["가격 조사 기록 필수 항목 누락: " + ", ".join(missing)]
    if not isinstance(research.get("competitors"), list):
        return ["가격 조사 기록 오류: competitors는 목록이어야 합니다."]
    for index, competitor_record in enumerate(research["competitors"], start=1):
        required = (
            "seller", "storeName", "productUrl", "productName", "optionOrConfiguration",
            "productPrice", "customerDeliveryFee", "orderTotal", "checkedAt",
            "sameSpecificationConfirmed", "exclusionReason",
        )
        missing_competitor = [
            field for field in required if competitor_record.get(field) is None
        ]
        if missing_competitor:
            return [
                f"경쟁가 기록 {index}번 필수 항목 누락: "
                + ", ".join(missing_competitor)
            ]
        if competitor_record.get("sameSpecificationConfirmed") is True and "smartstore.naver.com/" not in str(competitor_record.get("productUrl", "")):
            return [f"경쟁가 기록 {index}번은 스마트스토어 직접 URL이 아닙니다."]

    evidence = research.get("priceEvidence")
    if not isinstance(evidence, dict) or evidence.get("verified") is not True:
        return ["사용자 검증 가능 가격 근거 미완료: priceEvidence.verified=true 필요"]
    if not evidence.get("checkedAt"):
        return ["가격 근거 확인 시각 누락: priceEvidence.checkedAt 필요"]

    procurement = evidence.get("procurement")
    required_procurement = (
        "sourceUrl", "seller", "productName", "productPrice", "deliveryFee",
        "orderTotal", "sameSpecificationConfirmed",
    )
    if not isinstance(procurement, dict) or any(procurement.get(key) in (None, "") for key in required_procurement):
        return ["매입가 근거 불완전: 원본 경로/URL·판매자·규격·상품가·배송비·결제총액 필요"]
    if procurement.get("sameSpecificationConfirmed") is not True:
        return ["매입가 동일 규격 검증 미완료"]

    competitor = evidence.get("competitor")
    if not isinstance(competitor, dict) or competitor.get("status") not in {"verified", "not_found"}:
        return ["경쟁가 검증 상태 누락: priceEvidence.competitor.status 필요"]
    if not competitor.get("searchUrl"):
        return ["경쟁가 검색 URL 누락"]
    if competitor.get("status") == "verified":
        required_competitor = (
            "seller", "productName", "productUrl", "productPrice",
            "customerDeliveryFee", "orderTotal", "sameSpecificationConfirmed",
        )
        if any(competitor.get(key) in (None, "") for key in required_competitor):
            return ["경쟁가 근거 불완전: 판매자·직접 URL·규격·상품가·배송비·결제총액 필요"]
        if competitor.get("sameSpecificationConfirmed") is not True:
            return ["경쟁가 동일 규격 검증 미완료"]
        if "smartstore.naver.com/" not in str(competitor.get("productUrl", "")):
            return ["경쟁가 비교 대상 오류: 네이버 스마트스토어 직접 상품 URL만 허용"]
    return []


def image_processing_errors(product_dir: Path, listing: dict) -> list[str]:
    """등록할 이미지가 실제 가공 결과인지 processing manifest로 확인한다."""
    manifest_path = product_dir / "output" / "images" / "processing-manifest.json"
    if not manifest_path.exists():
        return ["이미지 가공 이력 없음: output/images/processing-manifest.json 필요"]
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"이미지 가공 이력을 읽을 수 없음: {exc}"]
    if not isinstance(manifest, list):
        return ["이미지 가공 이력 형식 오류: 목록이어야 합니다."]

    processed: set[Path] = set()
    for record in manifest:
        if record.get("error"):
            return [f"이미지 가공 실패: {record.get('source', '알 수 없는 원본')}"]
        if not record.get("source_sha256") or not record.get("transform"):
            return ["이미지 가공 이력 불완전: 원본 해시 또는 변환 내용 누락"]
        for output in record.get("outputs", []):
            path = Path(output.get("path", ""))
            if not path or not output.get("sha256"):
                return ["이미지 가공 이력 불완전: 출력 경로 또는 출력 해시 누락"]
            processed.add(path.resolve())

    errors = []
    for relative_path in listing.get("images", []):
        selected = (product_dir / relative_path).resolve()
        if not selected.exists():
            errors.append(f"등록 이미지 파일 없음: {relative_path}")
        elif selected not in processed:
            errors.append(f"등록 이미지가 가공 이력에 없음: {relative_path}")
    return errors


def sanity_check(listing: dict, pricing_cfg: dict) -> list[str]:
    """등록 불가 사유 목록을 반환한다. 비어 있으면 통과."""
    errors = []
    for field in REQUIRED_FIELDS:
        if not listing.get(field):
            errors.append(f"필수 필드 누락: {field}")

    # 검색 적합도에 직접 쓰이는 정보는 상품 라벨·공급처 근거로 반드시 채운다.
    # 단, 카테고리 속성은 네이버가 제공한 허용값과 실제 라벨값이 일치할 때만
    # 선택 입력하므로 값이 없다는 이유만으로 등록을 막지는 않는다.
    for field in SEO_REQUIRED_FIELDS:
        if not listing.get(field):
            errors.append(f"SEO 필수 필드 누락: {field}")
    if str(listing.get("name", "")).startswith(GENERIC_TITLE_LEADS):
        errors.append("상품명이 대용량·할인 등 일반 수식어로 시작함 — 제품군·규격을 먼저 배치 필요")
    keyword_research = listing.get("keywordResearchChecked")
    if keyword_research is False:
        errors.append("키워드 조사 실패 상태 — 검색량을 추정하지 말고 재조사 필요")

    sale_price = listing.get("salePrice", 0)
    if sale_price and sale_price <= 0:
        errors.append(f"판매가 오류: {sale_price}")

    customer_delivery_fee = listing.get(
        "customerDeliveryFee",
        listing.get("pricing", {}).get("customer_delivery_fee"),
    )
    minimum_fee = pricing_cfg.get("min_customer_delivery_fee", 3000)
    maximum_fee = pricing_cfg.get("max_customer_delivery_fee", 10000)
    if not isinstance(customer_delivery_fee, int):
        errors.append("고객 배송비 누락: customerDeliveryFee 또는 pricing.customer_delivery_fee 필요")
    elif not minimum_fee <= customer_delivery_fee <= maximum_fee:
        errors.append(
            f"고객 배송비 범위 오류: {customer_delivery_fee:,}원 "
            f"({minimum_fee:,}~{maximum_fee:,}원 필요)"
        )

    # 역마진/목표마진 검증 — listing.json의 pricing 블록(= pricing.py 출력) 기준
    pricing = listing.get("pricing", {})
    if not pricing.get("ok"):
        errors.append(f"가격 계산 실패 또는 마진 미달: {pricing.get('error', 'pricing 블록 없음')}")
    else:
        margin = pricing.get("margin_amount", 0)
        target = pricing_cfg.get("target_margin_rate", 0.10)
        rate = pricing.get("margin_rate_on_revenue", 0)
        if margin <= 0:
            errors.append(f"역마진: 마진 {margin}원")
        elif pricing.get("margin_rule") == "minimum_amount":
            minimum = pricing.get("minimum_margin_amount", 1000)
            if margin < minimum:
                errors.append(f"최소 순마진 미달: {margin}원 < {minimum}원")
        elif rate < target - 0.01:
            errors.append(f"목표마진 미달: {rate:.2%} < {target:.0%}")
        if pricing.get("sale_price") != sale_price:
            errors.append(
                f"listing.salePrice({sale_price})와 pricing.sale_price({pricing.get('sale_price')}) 불일치"
            )
        if customer_delivery_fee != pricing.get("customer_delivery_fee"):
            errors.append("listing 고객 배송비와 pricing 고객 배송비 불일치")

    tags = listing.get("sellerTags", [])
    if len(tags) > 10:
        errors.append(f"sellerTags {len(tags)}개 — 최대 10개")
    if len(tags) != len({tag.strip() for tag in tags if tag.strip()}):
        errors.append("sellerTags 중복 또는 빈 태그 포함")

    return errors


def upload_images(product_dir: Path, image_paths: list[str]) -> list[str]:
    """상품 이미지를 업로드하고 CDN URL 목록을 반환한다.
    이미지 업로드 API는 계정당 동시 1건만 허용되므로 단일 요청으로 순차 처리한다."""
    files = []
    for rel in image_paths:
        p = (product_dir / rel) if not Path(rel).is_absolute() else Path(rel)
        if not p.exists():
            raise FileNotFoundError(f"이미지 파일 없음: {p}")
        mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
        files.append(("imageFiles", (p.name, open(p, "rb"), mime)))

    try:
        resp = requests.post(
            IMAGE_UPLOAD_URL, headers=auth_headers(), files=files, timeout=120
        )
    finally:
        for _, (_, fh, _) in files:
            fh.close()

    if resp.status_code != 200:
        raise RuntimeError(f"이미지 업로드 실패 (HTTP {resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    urls = [img["url"] for img in data.get("images", [])]
    if not urls:
        raise RuntimeError(f"이미지 업로드 응답에 URL 없음: {data}")
    return urls


def resolve_processed_image_groups(product_dir: Path, image_paths: list[str]) -> list[list[str]]:
    """원본 이미지별 업로드 경로 묶음을 만든다.

    세로 상세 원본이 분할된 경우에도 그 조각들은 한 묶음으로 유지한다.
    """
    manifest_path = product_dir / "output" / "images" / "processing-manifest.json"
    split_outputs: dict[str, list[str]] = {}
    semantic_sections: set[str] = set()
    if manifest_path.exists():
        for result in load_json(manifest_path):
            outputs = result.get("outputs", [])
            if len(outputs) <= 1:
                continue
            source_stem = Path(result["source"]).stem
            split_outputs[source_stem] = [Path(item["path"]).name for item in outputs]
            if result.get("interleave_outputs"):
                semantic_sections.add(source_stem)

    groups = []
    for rel in image_paths:
        parts = split_outputs.get(Path(rel).stem)
        if parts:
            resolved = [str(Path(rel).parent / part) for part in parts]
            # 사람이 원본 내용의 끝을 확인해 나눈 섹션은 그 사이에 제품 소개를
            # 둘 수 있다. 그 밖의 분할 조각은 언제나 한 묶음으로 연속 표시한다.
            if Path(rel).stem in semantic_sections:
                groups.extend([[part] for part in resolved])
            else:
                groups.append(resolved)
        else:
            groups.append([rel])

    # 순서를 유지하면서 중복 파일을 제거한다. 분할 조각은 계속 붙어 있어야 한다.
    unique = list(dict.fromkeys(path for group in groups for path in group))
    if len(unique) > MAX_PRODUCT_IMAGES:
        raise ValueError(
            f"분할 후 이미지가 {len(unique)}장입니다. 네이버 등록 한도 {MAX_PRODUCT_IMAGES}장을 넘으므로 "
            "상세 원본을 더 적게 선택하거나 분할 기준을 조정하세요."
        )
    return groups


def resolve_processed_image_paths(product_dir: Path, image_paths: list[str]) -> list[str]:
    """기존 호출부 호환용: 원본 묶음을 평탄화한 실제 업로드 파일 목록."""
    return [
        path
        for group in resolve_processed_image_groups(product_dir, image_paths)
        for path in group
    ]


def direct_detail_keywords(keywords: Optional[list[str]]) -> list[str]:
    """상세 사이 설명에는 검증된 직접 연관 키워드만 최대 두 개 사용한다."""
    selected = []
    for keyword in keywords or []:
        cleaned = " ".join(str(keyword).split())
        if cleaned and len(cleaned) <= 30 and cleaned not in selected:
            selected.append(cleaned)
        if len(selected) == 2:
            break
    return selected


def common_detail_notices() -> tuple[str, str]:
    """공통 출고·재고 안내 이미지를 상세 상·하단에 넣는다.

    이미지 URL은 한 번만 스마트스토어 CDN에 올린 뒤 config/detail-notices.json에
    저장한다. URL이 아직 없으면 등록 자체를 막지 않고, 상세 본문은 그대로 만든다.
    다만 새 등록 전에는 업로드 스크립트로 URL을 준비하는 것이 원칙이다.
    """
    if not DETAIL_NOTICE_CONFIG_PATH.exists():
        return "", ""
    try:
        notices = load_json(DETAIL_NOTICE_CONFIG_PATH)
    except (OSError, json.JSONDecodeError):
        return "", ""
    top_url = str(notices.get("shippingPriorityUrl") or "").strip()
    bottom_url = str(notices.get("stockNoticeUrl") or "").strip()
    top = (
        '<section data-common-shipping-notice="true" '
        'style="margin:0 0 24px;">'
        f'<img src="{html.escape(top_url, quote=True)}" alt="출고 안내" '
        'style="display:block;width:100%;height:auto;margin:0;" />'
        '</section>'
        if top_url
        else ""
    )
    bottom = (
        '<section data-common-stock-notice="true" '
        'style="margin:32px 0 0;">'
        f'<img src="{html.escape(bottom_url, quote=True)}" alt="재고 및 주문 안내" '
        'style="display:block;width:100%;height:auto;margin:0;" />'
        '</section>'
        if bottom_url
        else ""
    )
    return top, bottom


def natural_image_story(label: str, value: str, fallback: str, index: int) -> tuple[str, str]:
    """검증된 표기만 사용해 이미지 사이에 자연스러운 짧은 소개를 만든다."""
    label = label.strip()
    value = value.strip()
    last = label[-1] if label else ""
    has_final_consonant = "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0
    topic = "은" if has_final_consonant else "는"
    if any(word in label for word in ("구성", "수량", "용량", "중량")):
        titles = ("한 번에 확인하는 구성", "이렇게 준비했습니다", "구성을 살펴보면")
        return titles[index % len(titles)], f"{label}{topic} {value}로 표기되어 있어요."
    if any(word in label for word in ("식품유형", "원재료", "성분")):
        titles = ("표기 정보를 먼저 살폈어요", "제품 정보를 확인해 보세요", "알아두면 좋은 표기")
        return titles[index % len(titles)], f"{label}{topic} {value}로 안내되어 있습니다."
    if any(word in label for word in ("제조", "원산지", "수입")):
        titles = ("구매 전 표기 확인", "제조·원산지 안내", "라벨에 적힌 정보")
        return titles[index % len(titles)], f"{label}{topic} {value}로 확인됩니다."
    titles = ("이미지와 함께 살펴보세요", "제품 정보를 정리하면", "다음 내용도 확인해 보세요")
    return titles[index % len(titles)], (f"{label}{topic} {value}입니다." if label and value else fallback)


def build_detail_content(
    detail_content: str,
    image_urls: list[str],
    detail_keywords: Optional[list[str]] = None,
    image_group_lengths: Optional[list[int]] = None,
) -> str:
    """상품 요약·실제 상품 사진·상세설명을 모바일에서 읽기 좋게 조합한다."""
    if not image_urls or 'data-product-image-gallery="true"' in detail_content:
        return detail_content

    # listing 초안의 {{IMAGE_1}} 자리표시자는 여기서 제거하지 않는다.
    # 아래 replace_placeholder가 실제 CDN 이미지 블록으로 교체하므로, 작성자가
    # 설계한 텍스트·이미지 순서(첫 이미지 → 설명 → 나머지 이미지)를 유지한다.

    # detail-page.md의 중앙 세로형 디자인을 등록 HTML에도 동일하게 적용한다.
    readable_content = (
        detail_content
        .replace("<h2>", '<h2 style="font-size:32px;line-height:1.5;margin:90px 20px 35px;text-align:center;color:#111;font-weight:700;word-break:keep-all;">')
        .replace("<h3>", '<h3 style="font-size:30px;line-height:1.5;margin:80px 20px 30px;text-align:center;color:#111;font-weight:700;word-break:keep-all;">')
        .replace("<p>", '<p style="font-size:22px;line-height:1.85;margin:30px 35px 70px;text-align:center;color:#222;word-break:keep-all;">')
        .replace("<ul>", '<ul style="font-size:22px;line-height:1.85;margin:30px 35px 70px;padding:0;list-style-position:inside;text-align:center;color:#222;word-break:keep-all;">')
        .replace("<table>", '<table style="width:100%;font-size:19px;line-height:1.7;margin:70px auto;border-collapse:collapse;color:#222;table-layout:fixed;text-align:center;">')
        .replace("<th>", '<th style="width:34%;padding:18px 14px;border:1px solid #dedbd5;background:#f7f5f1;text-align:center;color:#222;font-weight:700;vertical-align:middle;word-break:keep-all;">')
        .replace("<td>", '<td style="padding:18px 14px;border:1px solid #dedbd5;color:#222;text-align:center;vertical-align:middle;word-break:keep-all;">')
    )
    # listing.json에 이미 검증된 제목과 첫 설명 문장이 있으므로, 새 효능·사양을
    # 추정하지 않고 이 정보만으로 상세페이지 첫 화면의 간단한 설명을 만든다.
    heading_match = re.search(r"<h2[^>]*>(.*?)</h2>", detail_content, re.IGNORECASE | re.DOTALL)
    paragraph_matches = re.findall(r"<p[^>]*>(.*?)</p>", detail_content, re.IGNORECASE | re.DOTALL)
    heading = re.sub(r"<[^>]+>", "", heading_match.group(1) if heading_match else "상품 안내")
    composition = re.sub(r"<[^>]+>", "", paragraph_matches[0] if paragraph_matches else "상품의 구성과 보관 방법을 확인해 주세요.")
    emphasis = re.sub(r"<[^>]+>", "", paragraph_matches[1] if len(paragraph_matches) > 1 else composition)
    # 첫 화면에서 제목·구성·짧은 강조문을 이미 보여 주므로, 본문을 붙일 때 같은
    # h2·처음 두 문단을 제거한다. 상세 내용의 반복을 막고 이미지 전에 여백을 만든다.
    readable_body = re.sub(
        r'<h2[^>]*>.*?</h2>\s*<p[^>]*>.*?</p>(?:\s*<p[^>]*>.*?</p>)?',
        '',
        readable_content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    summary = (
        '<section data-product-summary="true" '
        'style="padding:80px 20px 55px;margin:0;text-align:center;">'
        f'<h2 style="font-size:42px;font-weight:800;line-height:1.4;margin:0 0 25px;color:#111;word-break:keep-all;">{html.escape(html.unescape(heading.strip()))}</h2>'
        f'<p style="font-size:28px;font-weight:700;line-height:1.55;margin:0 10px 28px;color:#222;word-break:keep-all;">{html.escape(html.unescape(composition.strip()))}</p>'
        f'<p style="font-size:31px;font-weight:500;line-height:1.65;margin:0 10px;color:#222;word-break:keep-all;">{html.escape(html.unescape(emphasis.strip()))}</p>'
        '</section>'
    )
    # 이미지 사이에 라벨 표의 사실을 기계적으로 SECTION으로 만들지 않는다.
    # 상세 작성자가 실제 특징과 연결해 넣은 {{IMAGE_n}} 자리만 CDN 이미지로 바꾼다.
    # 같은 원본에서 나뉜 세로 조각은 하나의 이미지 블록으로 계속 붙여 둔다.
    group_lengths = image_group_lengths or [1] * len(image_urls)
    if sum(group_lengths) != len(image_urls) or any(length < 1 for length in group_lengths):
        group_lengths = [1] * len(image_urls)
    image_blocks: list[list[str]] = []
    cursor = 0
    for length in group_lengths:
        image_blocks.append(image_urls[cursor:cursor + length])
        cursor += length

    def image_block(urls: list[str], block_index: int) -> str:
        margin = "20px 0 85px" if block_index == 0 else "45px 0 70px"
        images = "".join(
            f'<img src="{html.escape(url, quote=True)}" alt="상품 및 라벨 이미지 {block_index + 1}" '
            'style="max-width:100%;height:auto;display:block;margin:0 auto;" />'
            for url in urls
        )
        return f'<div data-product-image-block="{block_index + 1}" style="text-align:center;margin:{margin};">{images}</div>'

    placeholder_pattern = re.compile(
        r'<img\b[^>]*\{\{IMAGE_(\d+)\}\}[^>]*>', re.IGNORECASE
    )
    used_blocks: set[int] = set()

    def replace_placeholder(match: re.Match) -> str:
        block_index = int(match.group(1)) - 1
        if block_index < 0 or block_index >= len(image_blocks):
            return ""
        used_blocks.add(block_index)
        return image_block(image_blocks[block_index], block_index)

    has_placeholders = bool(placeholder_pattern.search(readable_body))
    readable_body = placeholder_pattern.sub(replace_placeholder, readable_body)
    if has_placeholders:
        # 자리표시자를 쓴 상세는 작성자가 텍스트와 이미지의 연결을 설계한 경우다.
        # 지정되지 않은 추가 이미지는 후반 상품 정보 앞에 억지로 삽입하지 않는다.
        gallery = ""
    else:
        # 기존 상세의 호환 경로다. 특징 SECTION은 자동 생성하지 않고 이미지만 연속 표시한다.
        gallery = (
            '<section data-product-image-gallery="true" style="text-align:center;">'
            f"{''.join(image_block(block, index) for index, block in enumerate(image_blocks))}"
            "</section>"
        )
    top_notice, bottom_notice = common_detail_notices()
    return (
        '<main data-smartstore-detail-layout="vertical-centered" '
        'style="max-width:860px;margin:0 auto;background:#fff;font-family:Arial,\'Noto Sans KR\',sans-serif;color:#111;line-height:1.8;text-align:center;word-break:keep-all;">'
        f"{top_notice}{summary}{gallery}<section style=\"text-align:center;\">{readable_body}</section>{bottom_notice}"
        "</main>"
    )


def build_payload(
    listing: dict,
    image_urls: list[str],
    store: dict,
    image_group_lengths: Optional[list[int]] = None,
) -> dict:
    """listing.json + store.json → 커머스API 상품 등록 페이로드"""
    delivery_fee_type = store.get("delivery_fee_type", "PAID")
    customer_delivery_fee = listing.get(
        "customerDeliveryFee",
        listing.get("pricing", {}).get(
            "customer_delivery_fee", store.get("base_delivery_fee", 0)
        ),
    )
    minimum_fee = store.get("min_customer_delivery_fee", 3000)
    maximum_fee = store.get("max_customer_delivery_fee", 10000)
    if (
        delivery_fee_type not in {"PAID", "UNIT_QUANTITY_PAID"}
        or not isinstance(customer_delivery_fee, int)
        or not minimum_fee <= customer_delivery_fee <= maximum_fee
    ):
        raise ValueError(
            f"유료 배송비는 {minimum_fee:,}~{maximum_fee:,}원으로 지정해야 합니다."
        )
    seller_tags = [{"text": t} for t in listing.get("sellerTags", [])[:10]]
    listing_origin = listing.get("originAreaInfo", {})
    origin_area_info = {
        "originAreaCode": listing_origin.get(
            "originAreaCode", store.get("origin_area_code", "0204000")
        ),
        "importer": listing_origin.get("importer", store.get("importer_name", "")),
    }
    if listing_origin.get("content"):
        origin_area_info["content"] = listing_origin["content"]
    if "plural" in listing_origin:
        origin_area_info["plural"] = listing_origin["plural"]

    origin_product = {
        "statusType": "SALE",
        "saleType": "NEW",
        "leafCategoryId": str(listing["leafCategoryId"]),
        "name": listing["name"],
        "detailContent": build_detail_content(
            listing["detailContent"],
            image_urls,
            listing.get("detailKeywords") or listing.get("sellerTags", []),
            image_group_lengths,
        ),
        "images": {
            "representativeImage": {"url": image_urls[0]},
            "optionalImages": [{"url": u} for u in image_urls[1:10]],
        },
        "salePrice": listing["salePrice"],
        "stockQuantity": listing["stockQuantity"],
        "deliveryInfo": {
            "deliveryType": "DELIVERY",
            "deliveryAttributeType": "NORMAL",
            "deliveryCompany": store.get("delivery_company", "CJGLS"),
            "deliveryBundleGroupUsable": store.get("delivery_bundle_group_usable", False),
            "deliveryFee": {
                "deliveryFeeType": delivery_fee_type,
                "baseFee": customer_delivery_fee,
                "deliveryFeePayType": store.get("delivery_fee_pay_type", "PREPAID"),
                **(
                    {"repeatQuantity": store.get("delivery_fee_repeat_quantity", 1)}
                    if delivery_fee_type == "UNIT_QUANTITY_PAID"
                    else {}
                ),
            },
            "claimDeliveryInfo": {
                "returnDeliveryFee": store.get("return_delivery_fee", 3000),
                "exchangeDeliveryFee": store.get("exchange_delivery_fee", 6000),
            },
        },
        "detailAttribute": {
            "afterServiceInfo": {
                "afterServiceTelephoneNumber": store.get("after_service_telephone", ""),
                "afterServiceGuideContent": store.get("after_service_guide", ""),
            },
            "originAreaInfo": origin_area_info,
            "minorPurchasable": store.get("minor_purchasable", True),
            "taxType": store.get("tax_type", "SALE"),
            "naverShoppingSearchInfo": {
                k: v
                for k, v in {
                    "brandName": listing.get("brandName", ""),
                    "manufacturerName": listing.get("manufacturerName", ""),
                    "modelName": listing.get("modelName", ""),
                }.items()
                if v
            },
            "sellerCommentUsable": False,
        },
    }
    # 상품정보제공고시와 단위가격은 식품 등 해당 카테고리에서 필수다.
    # 값은 listing.json에 라벨/공급처 근거로 기록한 경우에만 전달한다.
    if listing.get("productInfoProvidedNotice"):
        origin_product["detailAttribute"]["productInfoProvidedNotice"] = listing[
            "productInfoProvidedNotice"
        ]
    if listing.get("certificationTargetExcludeContent"):
        origin_product["detailAttribute"]["certificationTargetExcludeContent"] = listing[
            "certificationTargetExcludeContent"
        ]
    if listing.get("productCertificationInfos"):
        origin_product["detailAttribute"]["productCertificationInfos"] = listing[
            "productCertificationInfos"
        ]
    if listing.get("unitCapacity"):
        origin_product["detailAttribute"]["unitCapacity"] = listing["unitCapacity"]

    if seller_tags:
        origin_product["detailAttribute"]["seoInfo"] = {"sellerTags": seller_tags}

    # 카테고리 속성값 (검색 노출용) — listing에서 채운 경우만 포함
    if listing.get("attributes"):
        origin_product["detailAttribute"]["productAttributes"] = listing["attributes"]

    # 단독형 옵션 (선택)
    if listing.get("simpleOptions"):
        origin_product["detailAttribute"]["optionInfo"] = {
            "simpleOptionSortType": "CREATE",
            "optionSimple": listing["simpleOptions"],
        }

    return {
        "originProduct": origin_product,
        "smartstoreChannelProduct": {
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON",
        },
    }


def register(product_dir: Path) -> dict:
    listing_path = product_dir / "output" / "listing.json"
    if not listing_path.exists():
        raise FileNotFoundError(f"{listing_path} 가 없습니다. 먼저 listing.json을 생성하세요.")

    status_path = product_dir / "status.json"
    if status_path.exists():
        status = load_json(status_path)
        if status.get("status") == "registered":
            print(f"[=] 이미 등록됨 (productNo={status.get('productNo')}) — 스킵")
            return status

    listing = load_json(listing_path)
    # 등록 전 표 누락은 listing의 라벨·고시 기반 값으로 자동 보완한다. 이후에도
    # 중복 문단·표 항목 부족이 남으면 등록하지 않고 재작성 대상으로 남긴다.
    listing, repairs = repair_listing(listing)
    if repairs:
        listing_path.write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")
    pricing_cfg = load_json(PRICING_CONFIG_PATH)
    store = load_json(STORE_CONFIG_PATH)

    errors = (
        price_evidence_errors(product_dir)
        + image_processing_errors(product_dir, listing)
        + sanity_check(listing, pricing_cfg)
        + audit_listing(listing)
    )
    if errors:
        write_status(product_dir, status="error", errors=errors)
        print(f"[!] sanity check 실패 — 등록 스킵:")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    try:
        image_groups = resolve_processed_image_groups(product_dir, listing["images"])
        image_paths = [path for group in image_groups for path in group]
        print(f"[*] 이미지 업로드 중 ({len(image_paths)}장)...")
        image_urls = upload_images(product_dir, image_paths)
        print(f"[+] 이미지 업로드 완료: {len(image_urls)}개 URL")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        write_status(product_dir, status="error", errors=[str(e)])
        print(f"[!] {e}")
        sys.exit(1)

    payload = build_payload(listing, image_urls, store, [len(group) for group in image_groups])

    print(f"[*] 상품 등록 요청: {listing['name']}")
    resp = requests.post(
        PRODUCT_URL,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        write_status(
            product_dir,
            status="error",
            errors=[f"등록 API 실패 (HTTP {resp.status_code})"],
            api_response=resp.text[:2000],
        )
        print(f"[!] 등록 실패 (HTTP {resp.status_code}): {resp.text[:1000]}")
        sys.exit(1)

    data = resp.json()
    result = {
        "status": "registered",
        "productNo": data.get("smartstoreChannelProductNo") or data.get("productNo"),
        "originProductNo": data.get("originProductNo"),
        "salePrice": listing["salePrice"],
        "registered_at": datetime.now().isoformat(),
    }
    if result["productNo"]:
        result["publicProductUrl"] = (
            f"https://smartstore.naver.com/main/products/{result['productNo']}"
        )
    write_status(product_dir, _clear_errors=True, **result)
    print(
        f"[+] 등록 성공! productNo={result['productNo']}, "
        f"originProductNo={result['originProductNo']}, "
        f"publicUrl={result.get('publicProductUrl', '')}"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="listing.json 기반 스마트스토어 상품 등록")
    parser.add_argument("product_dir", help="상품 폴더 경로 (예: products/kirkland-almond)")
    args = parser.parse_args()
    register(Path(args.product_dir))


if __name__ == "__main__":
    main()
