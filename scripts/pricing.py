# 원가 → 판매가/마진 계산 (역마진 방지 하드가드 포함)
#
# 계산식 (매출 기준 마진 역산):
#   출고 비용은 config/pricing.json의 shipping_cost(2,300원)로 관리한다.
#   총수수료율 f = (매출연동수수료율 + 결제수수료율) × VAT배수
#   판매가 P가 만족해야 하는 조건:
#     P - P×f - 원가 - 배송비 - 박스비 >= P × 목표마진율
# 고객에게 별도 배송비 D를 받는 경우, 최종 주문금액 R=P+D가 조건을 만족해야 한다.
#   → R = (원가 + 배송비 + 박스비) / (1 - f - 목표마진율), P = R-D
#
# 사용법:
#   python3 scripts/pricing.py --cost 25000
#   python3 scripts/pricing.py --cost 25000 --customer-delivery-fee 6000
#   python3 scripts/pricing.py --cost 25000 --sale-price 23780 \
#       --customer-delivery-fee 6000 --allow-minimum-margin
#   python3 scripts/pricing.py --cost 25000 --competitor-product-price 23790 \
#       --shift-price-to-shipping
#   python3 scripts/pricing.py --cost 25000 --target-product-price 23790
#   python3 scripts/pricing.py --cost 25000 --pricing-config config/pricing.json
# 출력: JSON (ok=false면 역마진/마진미달 → 등록 스킵 대상)

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_CONFIG = ROOT / "config" / "pricing.json"


def load_pricing_config(path: Path = DEFAULT_PRICING_CONFIG) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def calc_price(
    cost: int,
    cfg: dict,
    customer_delivery_fee: Optional[int] = None,
    sale_price_override: Optional[int] = None,
    allow_minimum_margin: bool = False,
) -> dict:
    """한 개 기준 원가·수량별 고객 배송비로 상품가와 마진을 계산한다."""
    fee_rate = (
        cfg["sales_linkage_fee_rate"] + cfg["payment_fee_rate"]
    ) * cfg.get("vat_multiplier", 1.0)
    fixed_cost = cfg["shipping_cost"] + cfg["box_cost"]
    margin_rate = cfg["target_margin_rate"]
    unit = cfg.get("price_rounding_unit", 100)

    denominator = 1 - fee_rate - margin_rate
    if denominator <= 0:
        return {
            "ok": False,
            "error": f"수수료율({fee_rate:.4f}) + 목표마진율({margin_rate})이 1을 초과해 가격 산출 불가",
        }

    if customer_delivery_fee is None:
        customer_delivery_fee = cfg.get("customer_delivery_fee", 0)
    minimum_delivery_fee = cfg.get("min_customer_delivery_fee", 3000)
    maximum_delivery_fee = cfg.get("max_customer_delivery_fee", 10000)
    if customer_delivery_fee < minimum_delivery_fee:
        return {
            "ok": False,
            "error": f"고객 배송비는 {minimum_delivery_fee:,}원 이상이어야 합니다.",
        }
    if customer_delivery_fee > maximum_delivery_fee:
        return {
            "ok": False,
            "error": f"고객 배송비는 {maximum_delivery_fee:,}원 이하여야 합니다.",
        }
    raw_order_total = (cost + fixed_cost) / denominator
    sale_price = (
        sale_price_override
        if sale_price_override is not None
        else math.ceil((raw_order_total - customer_delivery_fee) / unit) * unit
    )
    if sale_price < 0:
        return {"ok": False, "error": "상품가는 0원 이상이어야 합니다."}
    order_total = sale_price + customer_delivery_fee

    fee_amount = round(order_total * fee_rate)
    total_cost = cost + fixed_cost + fee_amount
    margin_amount = order_total - total_cost
    margin_rate_actual = margin_amount / order_total if order_total > 0 else 0

    result = {
        "ok": True,
        "cost": cost,
        "sale_price": sale_price,
        "fee_rate": round(fee_rate, 4),
        "fee_amount": fee_amount,
        "shipping_cost": cfg["shipping_cost"],
        "customer_delivery_fee": customer_delivery_fee,
        "delivery_fee_type": cfg.get("delivery_fee_type", "UNIT_QUANTITY_PAID"),
        "repeat_quantity": cfg.get("delivery_fee_repeat_quantity", 1),
        "delivery_bundle_group_usable": cfg.get("delivery_bundle_group_usable", False),
        "order_total": order_total,
        "box_cost": cfg["box_cost"],
        "total_cost": total_cost,
        "margin_amount": margin_amount,
        "margin_rate_on_revenue": round(margin_rate_actual, 4),
        "target_margin_rate": margin_rate,
        "minimum_margin_amount": cfg.get("minimum_margin_amount", 1000),
        "min_customer_delivery_fee": minimum_delivery_fee,
        "max_customer_delivery_fee": maximum_delivery_fee,
        "margin_rule": "minimum_amount" if allow_minimum_margin else "target_rate",
    }

    # 역마진/목표마진 미달 하드가드 — 반올림 오차 1% 허용
    if margin_amount <= 0:
        result["ok"] = False
        result["error"] = f"역마진: 판매가 {sale_price}원에서 마진 {margin_amount}원"
    elif allow_minimum_margin and margin_amount < cfg.get("minimum_margin_amount", 1000):
        result["ok"] = False
        result["error"] = (
            f"최소 순마진 미달: {margin_amount}원 < "
            f"{cfg.get('minimum_margin_amount', 1000)}원"
        )
    elif not allow_minimum_margin and margin_rate_actual < margin_rate - 0.01:
        result["ok"] = False
        result["error"] = (
            f"목표마진 미달: 실마진율 {margin_rate_actual:.2%} < 목표 {margin_rate:.0%}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="원가 → 스마트스토어 판매가/마진 계산")
    parser.add_argument("--cost", type=int, required=True, help="원가 (코스트코 매입가, 원)")
    parser.add_argument("--pricing-config", default=str(DEFAULT_PRICING_CONFIG))
    parser.add_argument(
        "--customer-delivery-fee",
        type=int,
        help="상품별 고객 선결제 배송비. 생략하면 pricing.json 기본값을 사용합니다.",
    )
    parser.add_argument(
        "--quantity",
        type=int,
        default=1,
        help="수량별 배송 검증용 주문 수량(기본 1). 상품가와 배송비는 각 수량마다 적용됩니다.",
    )
    parser.add_argument(
        "--sale-price",
        type=int,
        help="검증할 상품가. 지정하면 해당 상품가·배송비의 실제 마진을 계산합니다.",
    )
    parser.add_argument(
        "--allow-minimum-margin",
        action="store_true",
        help="동일 규격 경쟁 총액과 충돌할 때 10%% 대신 최소 순마진만 검사합니다.",
    )
    parser.add_argument(
        "--competitor-product-price",
        type=int,
        help="동일 규격 경쟁 상품가. --shift-price-to-shipping과 함께 사용하면 이 가격보다 10원 낮게 상품가를 배치합니다.",
    )
    parser.add_argument(
        "--competitor-undercut",
        type=int,
        default=10,
        help="경쟁 상품가에서 뺄 금액(기본 10원).",
    )
    parser.add_argument(
        "--shift-price-to-shipping",
        action="store_true",
        help="목표 10%% 주문총액을 유지하면서 경쟁가 인하분을 고객 배송비로 배치합니다.",
    )
    parser.add_argument(
        "--target-product-price",
        type=int,
        help=(
            "상품가를 지정하고, 10%% 목표 주문총액을 만들기 위해 필요한 고객 배송비를 역산합니다. "
            "부피·중량 상품에서 상품가 일부를 배송비로 옮길 때 사용합니다."
        ),
    )
    args = parser.parse_args()

    cfg = load_pricing_config(Path(args.pricing_config))
    if args.shift_price_to_shipping and args.target_product_price is not None:
        parser.error("배송비 재배치 계산에서는 --shift-price-to-shipping과 --target-product-price 중 하나만 지정할 수 있습니다.")

    if args.target_product_price is not None:
        if args.sale_price is not None or args.customer_delivery_fee is not None:
            parser.error("--target-product-price에는 --sale-price와 --customer-delivery-fee를 함께 지정할 수 없습니다.")
        if args.target_product_price < 0:
            parser.error("--target-product-price는 0원 이상이어야 합니다.")

        fee_rate = (
            cfg["sales_linkage_fee_rate"] + cfg["payment_fee_rate"]
        ) * cfg.get("vat_multiplier", 1.0)
        target_order_total = math.ceil(
            (args.cost + cfg["shipping_cost"] + cfg["box_cost"])
            / (1 - fee_rate - cfg["target_margin_rate"])
            / cfg.get("price_rounding_unit", 100)
        ) * cfg.get("price_rounding_unit", 100)
        derived_delivery_fee = target_order_total - args.target_product_price
        if derived_delivery_fee < 0:
            parser.error("지정한 상품가가 10% 마진 목표 주문총액보다 높습니다. 배송비를 음수로 설정할 수 없습니다.")
        result = calc_price(
            args.cost,
            cfg,
            derived_delivery_fee,
            args.target_product_price,
            False,
        )
        result["pricing_strategy"] = "target_product_price_to_shipping"
        result["delivery_fee_in_allowed_range"] = result["ok"]
    elif args.shift_price_to_shipping:
        if args.competitor_product_price is None:
            parser.error("--shift-price-to-shipping에는 --competitor-product-price가 필요합니다.")
        if args.sale_price is not None or args.customer_delivery_fee is not None:
            parser.error("배송비 재배치 계산에서는 --sale-price와 --customer-delivery-fee를 함께 지정할 수 없습니다.")
        if args.competitor_undercut < 0:
            parser.error("--competitor-undercut은 0원 이상이어야 합니다.")

        fee_rate = (
            cfg["sales_linkage_fee_rate"] + cfg["payment_fee_rate"]
        ) * cfg.get("vat_multiplier", 1.0)
        target_order_total = math.ceil(
            (args.cost + cfg["shipping_cost"] + cfg["box_cost"])
            / (1 - fee_rate - cfg["target_margin_rate"])
        / cfg.get("price_rounding_unit", 100)) * cfg.get("price_rounding_unit", 100)
        shifted_sale_price = args.competitor_product_price - args.competitor_undercut
        shifted_delivery_fee = target_order_total - shifted_sale_price
        if shifted_sale_price < 0 or shifted_delivery_fee < 0:
            parser.error("경쟁가 기준 상품가 또는 재배치 배송비가 음수가 됩니다.")
        result = calc_price(
            args.cost,
            cfg,
            shifted_delivery_fee,
            shifted_sale_price,
            False,
        )
        result["pricing_strategy"] = "competitor_price_to_shipping"
        result["competitor_product_price"] = args.competitor_product_price
        result["competitor_undercut"] = args.competitor_undercut
        result["delivery_fee_in_allowed_range"] = result["ok"]
    else:
        result = calc_price(
            args.cost,
            cfg,
            args.customer_delivery_fee,
            args.sale_price,
            args.allow_minimum_margin,
        )
    if args.quantity < 1:
        parser.error("--quantity는 1 이상이어야 합니다.")
    if result.get("ok"):
        result["order_quantity"] = args.quantity
        result["quantity_delivery_order_total"] = result["order_total"] * args.quantity
        result["quantity_delivery_customer_fee_total"] = result["customer_delivery_fee"] * args.quantity
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
