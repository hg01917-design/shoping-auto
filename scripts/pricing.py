# 원가 → 판매가/마진 계산 (역마진 방지 하드가드 포함)
#
# 계산식 (매출 기준 마진 역산):
#   총수수료율 f = (매출연동수수료율 + 결제수수료율) × VAT배수
#   판매가 P가 만족해야 하는 조건:
#     P - P×f - 원가 - 배송비 - 박스비 >= P × 목표마진율
#   → P = (원가 + 배송비 + 박스비) / (1 - f - 목표마진율)  를 반올림 단위로 올림
#
# 사용법:
#   python3 scripts/pricing.py --cost 25000
#   python3 scripts/pricing.py --cost 25000 --pricing-config config/pricing.json
# 출력: JSON (ok=false면 역마진/마진미달 → 등록 스킵 대상)

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_CONFIG = ROOT / "config" / "pricing.json"


def load_pricing_config(path: Path = DEFAULT_PRICING_CONFIG) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def calc_price(cost: int, cfg: dict) -> dict:
    """원가와 pricing.json 파라미터로 판매가/마진을 계산한다."""
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

    raw_price = (cost + fixed_cost) / denominator
    sale_price = math.ceil(raw_price / unit) * unit

    fee_amount = round(sale_price * fee_rate)
    total_cost = cost + fixed_cost + fee_amount
    margin_amount = sale_price - total_cost
    margin_rate_actual = margin_amount / sale_price if sale_price > 0 else 0

    result = {
        "ok": True,
        "cost": cost,
        "sale_price": sale_price,
        "fee_rate": round(fee_rate, 4),
        "fee_amount": fee_amount,
        "shipping_cost": cfg["shipping_cost"],
        "box_cost": cfg["box_cost"],
        "total_cost": total_cost,
        "margin_amount": margin_amount,
        "margin_rate_on_revenue": round(margin_rate_actual, 4),
        "target_margin_rate": margin_rate,
    }

    # 역마진/목표마진 미달 하드가드 — 반올림 오차 1% 허용
    if margin_amount <= 0:
        result["ok"] = False
        result["error"] = f"역마진: 판매가 {sale_price}원에서 마진 {margin_amount}원"
    elif margin_rate_actual < margin_rate - 0.01:
        result["ok"] = False
        result["error"] = (
            f"목표마진 미달: 실마진율 {margin_rate_actual:.2%} < 목표 {margin_rate:.0%}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="원가 → 스마트스토어 판매가/마진 계산")
    parser.add_argument("--cost", type=int, required=True, help="원가 (코스트코 매입가, 원)")
    parser.add_argument("--pricing-config", default=str(DEFAULT_PRICING_CONFIG))
    args = parser.parse_args()

    cfg = load_pricing_config(Path(args.pricing_config))
    result = calc_price(args.cost, cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
