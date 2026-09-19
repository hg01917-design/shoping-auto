"""등록 상품을 수량별 개별 배송으로 전환하고, 한 개 기준 마진을 다시 계산한다.

기본 대상은 products/*/status.json에서 등록 완료된 상품이다. 상품별 원가와 현재
상품가를 사용해 고객 배송비를 역산한다. 목표 10%가 1만원 배송비로 불가능하면
최소 순마진 1,000원을 먼저 시도하고, 그래도 부족할 때만 상품가를 올린다.

사용법:
    python3 scripts/set_quantity_delivery.py --registered-all --dry-run
    python3 scripts/set_quantity_delivery.py --registered-all
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers
from pricing import calc_price, load_pricing_config


ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "config" / "store.json"
PRODUCTS_PATH = ROOT / "products"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def round_up(value: float, unit: int) -> int:
    return math.ceil(value / unit) * unit


def select_unit_price(cost: int, sale_price: int, cfg: dict) -> tuple[int, int, dict, str]:
    """한 개 기준 10%→최소 1천원 순서로 배송비·판매가를 확정한다."""
    fee_rate = (cfg["sales_linkage_fee_rate"] + cfg["payment_fee_rate"]) * cfg.get(
        "vat_multiplier", 1.0
    )
    fixed_cost = cfg["shipping_cost"] + cfg["box_cost"]
    unit = cfg.get("price_rounding_unit", 100)
    min_fee = cfg.get("min_customer_delivery_fee", 3000)
    max_fee = cfg.get("max_customer_delivery_fee", 10000)

    target_total = round_up(
        (cost + fixed_cost) / (1 - fee_rate - cfg["target_margin_rate"]), unit
    )
    target_fee = max(min_fee, round_up(target_total - sale_price, unit))
    if target_fee <= max_fee:
        calculated = calc_price(cost, cfg, target_fee, sale_price)
        if calculated["ok"]:
            return sale_price, target_fee, calculated, "target_margin_10_percent"

    minimum_total = round_up(
        (cost + fixed_cost + cfg.get("minimum_margin_amount", 1000)) / (1 - fee_rate),
        unit,
    )
    minimum_fee = max(min_fee, round_up(minimum_total - sale_price, unit))
    if minimum_fee <= max_fee:
        calculated = calc_price(cost, cfg, minimum_fee, sale_price, True)
        if calculated["ok"]:
            return sale_price, minimum_fee, calculated, "minimum_margin_1000"

    # 배송비 상한으로도 최소 마진이 안 나면 판매가를 올려 역마진을 차단한다.
    adjusted_sale_price = max(sale_price, round_up(minimum_total - max_fee, unit))
    calculated = calc_price(cost, cfg, max_fee, adjusted_sale_price, True)
    if not calculated["ok"]:
        raise ValueError(calculated.get("error", "수량별 배송 가격 계산 실패"))
    return adjusted_sale_price, max_fee, calculated, "minimum_margin_1000_price_adjusted"


def registered_product_dirs() -> list[Path]:
    result = []
    for status_path in sorted(PRODUCTS_PATH.glob("*/status.json")):
        try:
            status = load_json(status_path)
        except (OSError, json.JSONDecodeError):
            continue
        if status.get("status") == "registered" and status.get("originProductNo"):
            result.append(status_path.parent)
    return result


def update_one(product_dir: Path, cfg: dict, store: dict, dry_run: bool) -> dict:
    status_path = product_dir / "status.json"
    listing_path = product_dir / "output" / "listing.json"
    status = load_json(status_path)
    listing = load_json(listing_path)
    origin_product_no = str(status["originProductNo"])
    cost = listing.get("pricing", {}).get("cost")
    sale_price = listing.get("salePrice")
    if not isinstance(cost, int) or not isinstance(sale_price, int):
        return {
            "productDir": product_dir.name,
            "originProductNo": origin_product_no,
            "updated": False,
            "reason": "listing에 원가 또는 판매가가 없어 상품별 배송비를 계산할 수 없음",
        }

    new_sale_price, customer_fee, pricing, strategy = select_unit_price(cost, sale_price, cfg)
    result = {
        "productDir": product_dir.name,
        "originProductNo": origin_product_no,
        "oldSalePrice": sale_price,
        "newSalePrice": new_sale_price,
        "customerDeliveryFee": customer_fee,
        "expectedUnitTotal": pricing["order_total"],
        "expectedTwoUnitTotal": pricing["order_total"] * 2,
        "expectedNetMargin": pricing["margin_amount"],
        "strategy": strategy,
        "updated": False,
    }
    if dry_run:
        result["dryRun"] = True
        return result

    url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    response = requests.get(url, headers=auth_headers(), timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"{origin_product_no} 조회 실패 HTTP {response.status_code}: {response.text[:500]}")
    origin_product = response.json()["originProduct"]
    origin_product["salePrice"] = new_sale_price
    delivery_info = origin_product.setdefault("deliveryInfo", {})
    delivery_info["deliveryBundleGroupUsable"] = False
    delivery_info.pop("deliveryBundleGroupId", None)
    delivery_fee = delivery_info.setdefault("deliveryFee", {})
    delivery_fee.update(
        {
            "deliveryFeeType": "UNIT_QUANTITY_PAID",
            "baseFee": customer_fee,
            "repeatQuantity": 1,
            "deliveryFeePayType": store.get("delivery_fee_pay_type", "PREPAID"),
        }
    )
    response = requests.put(
        url,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json={"originProduct": origin_product},
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"{origin_product_no} 수정 실패 HTTP {response.status_code}: {response.text[:1000]}")

    listing["salePrice"] = new_sale_price
    listing["customerDeliveryFee"] = customer_fee
    listing["pricing"] = pricing
    listing["deliveryPolicy"] = {
        "deliveryFeeType": "UNIT_QUANTITY_PAID",
        "repeatQuantity": 1,
        "deliveryBundleGroupUsable": False,
        "calculatedAt": datetime.now(timezone.utc).isoformat(),
        "strategy": strategy,
    }
    dump_json(listing_path, listing)
    status["salePrice"] = new_sale_price
    status["customerDeliveryFee"] = customer_fee
    status["deliveryFeeType"] = "UNIT_QUANTITY_PAID"
    status["deliveryFeeRepeatQuantity"] = 1
    status["deliveryBundleGroupUsable"] = False
    status["delivery_updated_at"] = datetime.now(timezone.utc).isoformat()
    dump_json(status_path, status)

    research_path = product_dir / "output" / "price-research.json"
    research = load_json(research_path) if research_path.exists() else {}
    history = research.setdefault("deliveryPolicyHistory", [])
    history.append(
        {
            "changedAt": datetime.now(timezone.utc).isoformat(),
            "deliveryFeeType": "UNIT_QUANTITY_PAID",
            "repeatQuantity": 1,
            "deliveryBundleGroupUsable": False,
            "salePrice": new_sale_price,
            "customerDeliveryFee": customer_fee,
            "expectedUnitTotal": pricing["order_total"],
            "expectedTwoUnitTotal": pricing["order_total"] * 2,
            "expectedNetMargin": pricing["margin_amount"],
            "strategy": strategy,
        }
    )
    dump_json(research_path, research)
    result["updated"] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="등록 상품을 수량별 개별배송으로 일괄 전환")
    parser.add_argument("product_dirs", nargs="*", help="상품 폴더 경로")
    parser.add_argument("--registered-all", action="store_true", help="등록 완료된 프로젝트 상품 전체")
    parser.add_argument("--dry-run", action="store_true", help="계산만 하고 API 수정은 하지 않음")
    parser.add_argument("--offset", type=int, default=0, help="등록 상품 목록의 시작 위치(0부터)")
    parser.add_argument("--limit", type=int, help="한 번에 처리할 최대 상품 수")
    args = parser.parse_args()
    if not args.registered_all and not args.product_dirs:
        parser.error("상품 폴더 또는 --registered-all 중 하나가 필요합니다.")

    targets = [Path(value) for value in args.product_dirs]
    if args.registered_all:
        targets.extend(registered_product_dirs())
    targets = list(dict.fromkeys(target.resolve() for target in targets))
    if args.offset < 0:
        parser.error("--offset은 0 이상이어야 합니다.")
    targets = targets[args.offset : args.offset + args.limit if args.limit else None]
    cfg = load_pricing_config()
    store = load_json(STORE_PATH)
    outcomes = []
    for target in targets:
        try:
            outcomes.append(update_one(target, cfg, store, args.dry_run))
        except Exception as exc:
            outcomes.append({"productDir": target.name, "updated": False, "reason": str(exc)})
    print(json.dumps({"dryRun": args.dry_run, "results": outcomes}, ensure_ascii=False, indent=2))
    if any(not item.get("updated") for item in outcomes) and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
