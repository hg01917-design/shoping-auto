"""검증된 상품 근거와 네이버 카테고리 속성값을 대조해 속성 후보를 만든다.

사용법:
    python3 scripts/prepare_product_attributes.py

속성값은 라벨·공급처 근거(source.md), 현재 상품명, 기존 상세 정보 안에 실제로
표기된 값만 선택한다. 범위형 수치 속성은 단위·구간을 별도로 검증하기 전까지
자동 입력하지 않는다.
"""

import html
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers


ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "config" / "category-attribute-values.json"
MEANINGLESS_VALUES = {"기타", "본품", "일반", "기본", "전체", "없음", "미분류"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", value.lower())


def fetch_category_values(category_id: str) -> list[dict]:
    for attempt, delay in enumerate((2, 5, 10), start=1):
        response = requests.get(
            f"{API_BASE}/v1/product-attributes/attribute-values",
            headers=auth_headers(),
            params={"categoryId": category_id},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        # 일부 리프 카테고리는 속성 목록 자체를 제공하지 않는다. 이 경우 임의의
        # 속성값을 만들지 않고 빈 목록으로 캐시하여 다른 카테고리 검증을 계속한다.
        if response.status_code == 404:
            return []
        if response.status_code != 429 or attempt == 3:
            raise RuntimeError(
                f"카테고리 {category_id} 속성값 조회 실패 (HTTP {response.status_code}): {response.text[:500]}"
            )
        time.sleep(delay)
    raise RuntimeError(f"카테고리 {category_id} 속성값 조회 재시도 실패")


def collect_catalog(category_ids: set[str]) -> dict[str, list[dict]]:
    cache = load_json(CACHE_PATH) if CACHE_PATH.exists() else {}
    catalog = cache.get("categories", {})
    changed = False
    for category_id in sorted(category_ids):
        if category_id in catalog:
            continue
        catalog[category_id] = fetch_category_values(category_id)
        changed = True
        # 상품 속성 API는 짧은 시간의 연속 호출에 제한이 있으므로 카테고리별로
        # 간격을 둔다. 매 성공 직후 캐시를 써서 다음 실행에서 이어받는다.
        write_json(CACHE_PATH, {"fetched_at": datetime.now().isoformat(), "categories": catalog})
        time.sleep(1.2)
    if changed or not CACHE_PATH.exists():
        write_json(CACHE_PATH, {"fetched_at": datetime.now().isoformat(), "categories": catalog})
    return catalog


def evidence_for(product_dir: Path, listing: dict) -> list[str]:
    # 초기 등록분은 input/source.md, 0907 신규 등록분은 상품 루트의 source.md에
    # 원본 라벨·공식 고시 근거를 보관했다. 둘 중 실제로 존재하는 근거만 사용한다.
    source_path = product_dir / "input" / "source.md"
    if not source_path.exists():
        source_path = product_dir / "source.md"
    source = source_path.read_text(encoding="utf-8")
    detail = html.unescape(re.sub(r"<[^>]+>", "\n", listing.get("detailContent", "")))
    # 숫자·기호 값이 서로 다른 문장 경계를 넘어 우연히 결합하지 않도록, 각 줄과
    # 필드를 별개의 근거 단위로 유지한다.
    return [
        segment.strip()
        for segment in [*source.splitlines(), listing.get("name", ""), *listing.get("sellerTags", []), *detail.splitlines()]
        if segment.strip()
    ]


def value_is_in_evidence(value: str, evidence_segments: list[str]) -> bool:
    """숫자형 값은 원문 표기 그대로, 일반 값은 공백·기호를 무시해 비교한다."""
    if re.fullmatch(r"[A-Za-z]{2,}", value):
        # PB·PLA처럼 짧은 영문 속성값은 다른 영단어 일부와 일치하면 안 된다.
        pattern = rf"(?<![A-Za-z]){re.escape(value)}(?![A-Za-z])"
        return any(re.search(pattern, segment, re.IGNORECASE) for segment in evidence_segments)
    if any(character.isdigit() for character in value):
        pattern = re.escape(value).replace(r"\ ", r"\s*")
        return any(re.search(pattern, segment, re.IGNORECASE) for segment in evidence_segments)
    normalized_value = normalize(value)
    return any(normalized_value in normalize(segment) for segment in evidence_segments)


def select_attributes(values: list[dict], evidence_segments: list[str]) -> list[dict]:
    """선택형 값 가운데 근거에 명시된 값만 반환한다."""
    selected = defaultdict(list)
    limits = {}
    for item in values:
        value = (item.get("minAttributeValue") or "").strip()
        # 범위형은 min/max가 함께 온다. 591ml처럼 실제값과 구간코드를 함께 넣으려면
        # 단위 검증이 필요하므로 자동 입력 대상에서 제외한다.
        if (
            item.get("minAttributeValueUnitCode")
            or item.get("maxAttributeValueUnitCode")
            or item.get("maxAttributeValue") is not None
        ):
            continue
        if value in MEANINGLESS_VALUES or len(normalize(value)) < 2:
            continue
        if not value_is_in_evidence(value, evidence_segments):
            continue
        attribute_seq = item["attributeSeq"]
        if any(entry["attributeValueSeq"] == item["attributeValueSeq"] for entry in selected[attribute_seq]):
            continue
        selected[attribute_seq].append(
            {"attributeSeq": attribute_seq, "attributeValueSeq": item["attributeValueSeq"]}
        )

    # API가 속성별 최대 선택 수를 값 목록에는 제공하지 않으므로, 안전하게 속성당
    # 최대 3개까지만 담는다. 이는 복수 선택형의 일반적인 허용 범위 안이다.
    result = []
    for attribute_seq in sorted(selected):
        result.extend(selected[attribute_seq][: limits.get(attribute_seq, 3)])
    return result


def default_pet_pad_tags() -> list[str]:
    return ["애견패드", "강아지배변패드", "흡수패드", "커클랜드펫패드", "100매패드"]


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="검증 근거와 카테고리 속성값을 대조해 상품 속성을 준비"
    )
    parser.add_argument(
        "--product-dir",
        action="append",
        default=[],
        help="등록 전 상품 폴더. 지정하면 registered 상태가 아니어도 해당 폴더만 처리",
    )
    args = parser.parse_args()

    product_dirs = []
    category_ids = set()
    if args.product_dir:
        candidates = [ROOT / item for item in args.product_dir]
    else:
        candidates = []
        for status_path in sorted((ROOT / "products").glob("*/status.json")):
            status = load_json(status_path)
            if status.get("status") == "registered":
                candidates.append(status_path.parent)

    for product_dir in candidates:
        if not product_dir.is_dir():
            raise FileNotFoundError(f"상품 폴더 없음: {product_dir}")
        listing = load_json(product_dir / "output" / "listing.json")
        product_dirs.append((product_dir, listing))
        category_ids.add(str(listing["leafCategoryId"]))

    catalog = collect_catalog(category_ids)
    report = {"generated_at": datetime.now().isoformat(), "products": []}
    for product_dir, listing in product_dirs:
        if product_dir.name == "kirkland-pet-pad-100ct" and not listing.get("sellerTags"):
            listing["sellerTags"] = default_pet_pad_tags()
        attributes = select_attributes(catalog[str(listing["leafCategoryId"])], evidence_for(product_dir, listing))
        listing["attributes"] = attributes
        write_json(product_dir / "output" / "listing.json", listing)
        report["products"].append(
            {
                "slug": product_dir.name,
                "category_id": str(listing["leafCategoryId"]),
                "seller_tag_count": len(listing.get("sellerTags", [])),
                "attributes": attributes,
            }
        )

    report_path = ROOT / "output" / "product-attribute-preparation-report.json"
    write_json(report_path, report)
    with_attributes = sum(bool(item["attributes"]) for item in report["products"])
    print(f"[=] 대상 {len(report['products'])}건, 속성 후보 있음 {with_attributes}건 → {report_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"[!] {error}", file=sys.stderr)
        sys.exit(1)
