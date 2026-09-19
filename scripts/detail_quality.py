"""스마트스토어 상세페이지의 표·중복 문단 품질을 점검하고 최소 요건을 보완한다.

신규 등록 전에는 register_product.py가 이 모듈을 호출한다. 이미 등록된 상품은
`python3 scripts/detail_quality.py --apply` 후 update_product_detail.py로 반영한다.
"""

import argparse
import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ABSTRACT_SECTION_TITLES = (
    "한 번에 확인하는 구성",
    "제품 정보를 확인해 보세요",
    "상품 정보를 확인해 보세요",
    "라벨에 적힌 정보",
    "자세히 알아볼까요",
    "제품 특징을 살펴보세요",
    "이런 점이 좋아요",
    "구성 확인",
    "기본 정보",
    "제품 안내",
)


def plain(value: object) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    return " ".join(html.unescape(text).split())


def first_sentence(value: object) -> str:
    text = plain(value)
    if not text:
        return ""
    return re.split(r"(?<=[.!?])\s+|\n", text, maxsplit=1)[0]


def capacity_text(listing: dict) -> str:
    capacity = listing.get("unitCapacity") or {}
    total = capacity.get("totalCapacityValue")
    unit = capacity.get("indicationUnit") or ""
    if total is None or not unit:
        return ""
    return f"{total}{unit}"


def basic_rows(listing: dict) -> list[tuple[str, str]]:
    """listing에 이미 검증돼 있는 정보만 상품 기본 정보 표 행으로 만든다."""
    rows: list[tuple[str, str]] = []
    notice = listing.get("productInfoProvidedNotice") or {}
    if notice.get("productInfoProvidedNoticeType") == "GENERAL_FOOD":
        food = notice.get("generalFood") or {}
        if food.get("amount"):
            rows.append(("구성", str(food["amount"])))
        if food.get("weight"):
            rows.append(("내용량", str(food["weight"])))
        if food.get("foodType"):
            rows.append(("식품유형", str(food["foodType"])))
        origin = plain((listing.get("originAreaInfo") or {}).get("content"))
        if origin:
            rows.append(("원산지", origin))
        storage = first_sentence(food.get("consumerSafetyCaution"))
        if storage:
            rows.append(("보관 방법", storage))
    else:
        amount = capacity_text(listing)
        if amount:
            rows.append(("구성", amount))
        model = plain(listing.get("modelName"))
        if model:
            rows.append(("모델", model))
        manufacturer = plain(listing.get("manufacturerName"))
        if manufacturer:
            rows.append(("제조사", manufacturer))
        origin = plain((listing.get("originAreaInfo") or {}).get("content"))
        if origin:
            rows.append(("원산지", origin))

    unique: list[tuple[str, str]] = []
    seen = set()
    for label, value in rows:
        key = (plain(label), plain(value))
        if key[0] and key[1] and key not in seen:
            unique.append(key)
            seen.add(key)
    return unique


def table_html(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"
        for label, value in rows
    )
    return f"<h2>상품 기본 정보</h2><table><tbody>{body}</tbody></table>"


def repair_listing(listing: dict) -> tuple[dict, list[str]]:
    """표가 없을 때만 검증된 listing 값으로 표를 추가한다."""
    detail = str(listing.get("detailContent") or "")
    repairs: list[str] = []
    if "<table" not in detail.lower():
        rows = basic_rows(listing)
        if len(rows) >= 3:
            table = table_html(rows)
            shipping = re.search(r"<h2[^>]*>[^<]*(배송|교환|반품)[^<]*</h2>", detail, re.I)
            if shipping:
                detail = detail[: shipping.start()] + table + detail[shipping.start() :]
            else:
                detail = detail.replace("</section>", table + "</section>", 1)
            listing["detailContent"] = detail
            repairs.append("상품 기본 정보 표 추가")
    return listing, repairs


def audit_listing(listing: dict) -> list[str]:
    detail = str(listing.get("detailContent") or "")
    errors: list[str] = []
    if "<table" not in detail.lower():
        errors.append("상세페이지 상품 기본 정보 표 누락")
    rows = re.findall(r"<tr[^>]*>.*?</tr>", detail, re.I | re.S)
    if len(rows) < 3:
        errors.append("상품 기본 정보 표 항목 부족")
    paragraphs = [plain(value) for value in re.findall(r"<p[^>]*>(.*?)</p>", detail, re.I | re.S)]
    paragraphs = [value for value in paragraphs if len(value) >= 18]
    if len(paragraphs) != len(set(paragraphs)):
        errors.append("상세 설명에 동일 문단 반복")
    if any(token in detail for token in ("제품을 살펴보면", "이미지와 함께 살펴보세요")):
        errors.append("상세 설명에 일반 반복 문구 포함")
    section_titles = [
        plain(value) for value in re.findall(r"<h3[^>]*>(.*?)</h3>", detail, re.I | re.S)
    ]
    blocked = [title for title in section_titles if title in ABSTRACT_SECTION_TITLES]
    if blocked:
        errors.append("상세 설명에 추상적 SECTION 제목 포함: " + ", ".join(blocked))
    if len(section_titles) > 5:
        errors.append("상세 중간 SECTION 과다: 핵심 특징만 남기고 통합 필요")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="상세페이지 표·중복 문단 점검/보완")
    parser.add_argument("--apply", action="store_true", help="표 누락 listing.json을 보완 저장")
    parser.add_argument("--registered-only", action="store_true")
    args = parser.parse_args()

    report = {"checked": 0, "repaired": [], "failed": []}
    for status_path in sorted((ROOT / "products").glob("*/status.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if args.registered_only and status.get("status") != "registered":
            continue
        listing_path = status_path.parent / "output" / "listing.json"
        if not listing_path.exists():
            continue
        listing = json.loads(listing_path.read_text(encoding="utf-8"))
        report["checked"] += 1
        listing, repairs = repair_listing(listing)
        errors = audit_listing(listing)
        if args.apply and repairs:
            listing_path.write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")
        if repairs:
            report["repaired"].append({"slug": status_path.parent.name, "repairs": repairs})
        if errors:
            report["failed"].append({"slug": status_path.parent.name, "errors": errors})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
