"""과거 등록 상품의 가격 조사 기록을 현재 검증 형식으로 보완한다.

가격을 바꾸지 않는다. 이미 listing.json에 저장된 계산값만 사용하며, 원가 출처나
동일 규격 스마트스토어 경쟁가가 남아 있지 않은 경우에는 추정하지 않고
``not_available`` 사유를 기록한다.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_KEYS = (
    "userImageCost",
    "costcoOfficialCost",
    "adoptedCost",
    "competitors",
    "targetMarginCalculation",
    "minimumMarginApplied",
    "finalProductPrice",
    "finalCustomerDeliveryFee",
    "totalPaymentAmount",
    "expectedNetMargin",
    "calculatedAt",
    "decisionReason",
)


def not_available(reason: str) -> dict:
    return {"status": "not_available", "reason": reason}


def normalized_research(existing: dict, listing: dict) -> dict:
    pricing = listing.get("pricing") or {}
    cost = pricing.get("cost")
    now = datetime.now(timezone.utc).isoformat()
    result = dict(existing)

    result.setdefault(
        "userImageCost",
        not_available("과거 등록 기록에 사용자 가격표 원본 근거가 남아 있지 않음"),
    )
    result.setdefault(
        "costcoOfficialCost",
        not_available("과거 등록 기록에 코스트코 공식몰 확인 시각·URL이 남아 있지 않음"),
    )
    result.setdefault(
        "adoptedCost",
        (
            {
                "status": "available",
                "value": cost,
                "source": "listing.pricing.cost",
                "note": "기존 등록 시 저장된 채택 원가; 외부 가격 재조사 전에는 변경하지 않음",
            }
            if isinstance(cost, int)
            else not_available("listing.pricing.cost가 없어 채택 원가를 복원할 수 없음")
        ),
    )
    result.setdefault(
        "competitors",
        [
            {
                "status": "not_available",
                "reason": "과거 등록 기록에 동일 규격 스마트스토어 경쟁 판매자·URL·배송비가 남아 있지 않음",
            }
        ],
    )
    result.setdefault(
        "targetMarginCalculation",
        {
            "status": "available" if pricing else "not_available",
            "value": pricing if pricing else None,
            "note": "기존 listing.pricing 계산값",
        },
    )
    result.setdefault(
        "minimumMarginApplied",
        pricing.get("margin_rule") == "minimum_amount",
    )
    result.setdefault("finalProductPrice", listing.get("salePrice"))
    result.setdefault("finalCustomerDeliveryFee", listing.get("customerDeliveryFee"))
    result.setdefault("totalPaymentAmount", pricing.get("order_total"))
    result.setdefault(
        "expectedNetMargin",
        {
            "amount": pricing.get("margin_amount"),
            "rateOnRevenue": pricing.get("margin_rate_on_revenue"),
        },
    )
    result.setdefault("calculatedAt", now)
    result.setdefault(
        "decisionReason",
        "과거 등록 가격 기록을 표준 형식으로 보완함. 최신 동일 규격 스마트스토어 경쟁가는 별도 재조사 전까지 미확정.",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="과거 상품 가격 조사 기록 표준화")
    parser.add_argument("--apply", action="store_true", help="price-research.json에 저장")
    args = parser.parse_args()

    scanned = changed = complete = 0
    missing_by_slug = []
    for status_path in sorted((ROOT / "products").glob("*/status.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") != "registered":
            continue
        listing_path = status_path.parent / "output" / "listing.json"
        if not listing_path.exists():
            missing_by_slug.append(status_path.parent.name)
            continue
        scanned += 1
        listing = json.loads(listing_path.read_text(encoding="utf-8"))
        research_path = status_path.parent / "output" / "price-research.json"
        existing = json.loads(research_path.read_text(encoding="utf-8")) if research_path.exists() else {}
        normalized = normalized_research(existing, listing)
        is_complete = all(key in normalized for key in REQUIRED_KEYS)
        complete += int(is_complete)
        if normalized != existing:
            changed += 1
            if args.apply:
                research_path.write_text(
                    json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
                )

    report = {
        "scanned": scanned,
        "wouldChange": changed,
        "complete": complete,
        "missingListing": missing_by_slug,
        "applied": args.apply,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
