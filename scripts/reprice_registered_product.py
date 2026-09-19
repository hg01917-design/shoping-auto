"""등록 상품의 10% 마진 가격·배송비를 검증해 로컬 listing에 반영한다.

실제 스마트스토어 반영은 이 스크립트 뒤에 update_product_detail.py를 순차 실행한다.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pricing import calc_price, load_pricing_config


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="등록 상품 가격·상품별 배송비 변경 준비")
    parser.add_argument("product_dir")
    parser.add_argument("--sale-price", type=int, required=True)
    parser.add_argument("--customer-delivery-fee", type=int, required=True)
    parser.add_argument("--competitor-name")
    parser.add_argument(
        "--competitor-url",
        help="동일 규격 경쟁 상품의 직접 링크(가격 확인 근거)입니다.",
    )
    parser.add_argument("--competitor-price", type=int)
    parser.add_argument("--competitor-delivery-fee", type=int)
    parser.add_argument("--same-specification", action="store_true")
    parser.add_argument(
        "--allow-delivery-fee-over-cap",
        action="store_true",
        help="사용자가 특정 상품에 대해 명시 승인한 배송비 상한 예외입니다.",
    )
    parser.add_argument("--delivery-fee-exception-reason")
    parser.add_argument(
        "--allow-lower-margin",
        action="store_true",
        help="동일 규격 경쟁가와 10%% 마진이 충돌할 때 최소 순마진 1,000원을 적용할 때 사용합니다.",
    )
    parser.add_argument(
        "--minimum-margin-reason",
        help="10%% 대신 최소 순마진을 적용한 경쟁가 확인 사유입니다.",
    )
    parser.add_argument(
        "--bulky-shipping-verified",
        action="store_true",
        help="실제 포장 부피·중량과 출고 운임을 확인했음을 기록합니다.",
    )
    parser.add_argument(
        "--bulky-shipping-evidence",
        help="포장 부피·중량 및 출고 운임의 확인 근거를 기록합니다.",
    )
    args = parser.parse_args()

    product_dir = Path(args.product_dir)
    listing_path = product_dir / "output" / "listing.json"
    status_path = product_dir / "status.json"
    listing = load_json(listing_path)
    status = load_json(status_path)
    if status.get("status") != "registered":
        raise ValueError("등록 완료 상품만 가격을 수정할 수 있습니다.")
    competitor_values = (
        args.competitor_name,
        args.competitor_price,
        args.competitor_delivery_fee,
    )
    if any(value is not None for value in competitor_values):
        if not all(value is not None for value in competitor_values):
            raise ValueError("경쟁가를 기록할 때는 이름·상품가·배송비를 모두 입력해야 합니다.")
        if not args.same_specification:
            raise ValueError("동일 규격 확인 없이 경쟁가를 기록할 수 없습니다.")
        if not args.competitor_url:
            raise ValueError("경쟁가를 반영할 때는 확인한 경쟁 상품의 직접 링크가 필요합니다.")

    cfg = load_pricing_config()
    if args.customer_delivery_fee > cfg.get("max_customer_delivery_fee", 6000):
        if not (
            args.allow_delivery_fee_over_cap
            and args.delivery_fee_exception_reason
        ):
            raise ValueError("고객 배송비가 설정된 상한을 초과합니다.")
    cost = listing.get("pricing", {}).get("cost")
    if not isinstance(cost, int):
        raise ValueError("listing.pricing.cost가 필요합니다.")

    regular = calc_price(cost, cfg, args.customer_delivery_fee)
    below_target_margin = (
        args.sale_price + args.customer_delivery_fee < regular["order_total"]
    )
    allow_minimum_margin = below_target_margin and args.allow_lower_margin
    if below_target_margin and not args.allow_lower_margin:
        needed_delivery_fee = max(
            cfg.get("customer_delivery_fee", 3000),
            regular["order_total"] - args.sale_price,
        )
        raise ValueError(
            "10% 마진을 위해 고객 배송비 "
            f"{needed_delivery_fee:,}원이 필요합니다(상한 {cfg.get('max_customer_delivery_fee', 6000):,}원). "
            "사용자에게 보고하고 명시 승인을 받아야 합니다."
        )
    if allow_minimum_margin and not args.minimum_margin_reason:
        raise ValueError(
            "10% 미만 마진은 동일 규격 경쟁가와의 충돌 사유를 기록해야 합니다. "
            "--minimum-margin-reason을 제공하세요."
        )
    pricing = calc_price(
        cost,
        cfg,
        args.customer_delivery_fee,
        args.sale_price,
        allow_minimum_margin,
    )
    if not pricing.get("ok"):
        raise ValueError(pricing.get("error", "가격 검증 실패"))

    fee = args.customer_delivery_fee
    detail = listing.get("detailContent", "")
    detail = re.sub(
        r"배송비는 고객 선결제\s*[\d,]+원",
        f"배송비는 고객 선결제 {fee:,}원",
        detail,
    )
    detail = re.sub(
        r"고객 배송비는\s*[\d,]+원",
        f"고객 배송비는 {fee:,}원",
        detail,
    )

    listing["salePrice"] = args.sale_price
    listing["customerDeliveryFee"] = fee
    listing["pricing"] = pricing
    listing["detailContent"] = detail
    listing_path.write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")

    research_path = product_dir / "output" / "price-research.json"
    research = load_json(research_path) if research_path.exists() else {}
    history = research.setdefault("history", [])
    history.append(
        {
            "researchedAt": datetime.now(timezone.utc).isoformat(),
            "procurementCost": cost,
            "competitor": (
                {
                    "source": "네이버 가격비교 검색 결과",
                    "productName": args.competitor_name,
                    "productUrl": args.competitor_url,
                    "productPrice": args.competitor_price,
                    "customerDeliveryFee": args.competitor_delivery_fee,
                    "orderTotal": args.competitor_price + args.competitor_delivery_fee,
                    "sameSpecificationConfirmed": True,
                }
                if args.competitor_name is not None
                else {"source": "미조사", "note": "10% 마진 기본가 산정에 경쟁가는 사용하지 않음"}
            ),
            "decision": {
                "salePrice": args.sale_price,
                "customerDeliveryFee": fee,
                "orderTotal": pricing["order_total"],
                "competitorOrderTotalGap": (
                    pricing["order_total"] - args.competitor_price - args.competitor_delivery_fee
                    if args.competitor_name is not None
                    else None
                ),
                "marginAmount": pricing["margin_amount"],
                "marginRateOnRevenue": pricing["margin_rate_on_revenue"],
                "marginRule": pricing["margin_rule"],
                "bulkyShippingVerified": bool(args.bulky_shipping_verified),
                "bulkyShippingEvidence": args.bulky_shipping_evidence,
                "minimumMarginReason": args.minimum_margin_reason,
                "deliveryFeeExceptionReason": args.delivery_fee_exception_reason,
            },
        }
    )
    research_path.write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"slug": product_dir.name, "pricing": pricing}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] {exc}")
        sys.exit(1)
