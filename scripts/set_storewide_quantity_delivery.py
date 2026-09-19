"""스마트스토어 판매중 상품 전체를 수량별 개별배송으로 전환한다.

프로젝트에 원가가 기록된 상품은 set_quantity_delivery.py에서 마진 기준 배송비를
먼저 계산한다. 이 스크립트는 그 외의 판매중 상품도 빠짐없이 수량별 배송 방식으로
전환하되, 원가 근거가 없으면 현재 고객 배송비는 보존하고 별도 감사 기록에 남긴다.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers


ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_PATH = ROOT / "products"
REPORT_PATH = ROOT / "research" / "storewide-quantity-delivery.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def known_project_origin_numbers() -> set[str]:
    values = set()
    for status_path in PRODUCTS_PATH.glob("*/status.json"):
        try:
            status = load_json(status_path)
        except (OSError, json.JSONDecodeError):
            continue
        if status.get("status") == "registered" and status.get("originProductNo"):
            values.add(str(status["originProductNo"]))
    return values


def fetch_all_products() -> list[dict]:
    items = []
    for page in range(1, 4):
        response = requests.post(
            f"{API_BASE}/v1/products/search",
            headers={**auth_headers(), "Content-Type": "application/json"},
            json={"page": page, "size": 100},
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"상품목록 {page}페이지 조회 실패 HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        items.extend(data.get("contents", []))
        if data.get("last"):
            break
    return items


def active_origin_products(items: list[dict]) -> list[dict]:
    active = []
    for item in items:
        channels = item.get("channelProducts", [])
        if any(channel.get("statusType") == "SALE" for channel in channels):
            active.append(item)
    return active


def apply_one(origin_product_no: str, dry_run: bool, minimum_free_fee: int) -> dict:
    url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    response = requests.get(url, headers=auth_headers(), timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"조회 실패 HTTP {response.status_code}: {response.text[:500]}")
    origin = response.json()["originProduct"]
    delivery_info = origin.setdefault("deliveryInfo", {})
    delivery_fee = delivery_info.setdefault("deliveryFee", {})
    base_fee = delivery_fee.get("baseFee")
    result = {
        "originProductNo": origin_product_no,
        "name": origin.get("name"),
        "baseFee": base_fee,
        "oldDeliveryFeeType": delivery_fee.get("deliveryFeeType"),
        "oldRepeatQuantity": delivery_fee.get("repeatQuantity"),
        "oldDeliveryBundleGroupUsable": delivery_info.get("deliveryBundleGroupUsable"),
        "updated": False,
    }
    converted_from_free = not isinstance(base_fee, int) or base_fee <= 0
    if converted_from_free:
        base_fee = minimum_free_fee
        result["baseFee"] = base_fee
        result["freeDeliveryConvertedToMinimumFee"] = True
    already_correct = (
        delivery_fee.get("deliveryFeeType") == "UNIT_QUANTITY_PAID"
        and delivery_fee.get("repeatQuantity") == 1
        and delivery_info.get("deliveryBundleGroupUsable") is False
        and not converted_from_free
    )
    if dry_run:
        result["wouldSet"] = {
            "deliveryFeeType": "UNIT_QUANTITY_PAID",
            "repeatQuantity": 1,
            "deliveryBundleGroupUsable": False,
        }
        return result
    if already_correct:
        result["updated"] = True
        result["unchanged"] = True
        return result
    delivery_info["deliveryBundleGroupUsable"] = False
    delivery_info.pop("deliveryBundleGroupId", None)
    delivery_fee.update(
        {
            "deliveryFeeType": "UNIT_QUANTITY_PAID",
            "repeatQuantity": 1,
            "baseFee": base_fee,
            "deliveryFeePayType": delivery_fee.get("deliveryFeePayType", "PREPAID"),
        }
    )
    response = requests.put(
        url,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json={"originProduct": origin},
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"수정 실패 HTTP {response.status_code}: {response.text[:800]}")
    result["updated"] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="판매중인 전체 상품을 수량별 개별배송으로 전환")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--minimum-free-fee",
        type=int,
        default=3000,
        help="기존 무료배송 상품을 유료배송으로 전환할 때 쓸 최소 배송비",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=1.25,
        help="네이버 API 요청 제한을 피하기 위한 상품별 처리 간격",
    )
    parser.add_argument(
        "--include-project-products",
        action="store_true",
        help="이미 프로젝트 계산기로 처리한 상품도 다시 처리합니다.",
    )
    args = parser.parse_args()
    if args.offset < 0:
        parser.error("--offset은 0 이상이어야 합니다.")
    items = active_origin_products(fetch_all_products())
    known = known_project_origin_numbers()
    if not args.include_project_products:
        items = [item for item in items if str(item.get("originProductNo")) not in known]
    items = items[args.offset : args.offset + args.limit if args.limit else None]
    results = []
    for item in items:
        origin_no = str(item["originProductNo"])
        try:
            result = apply_one(origin_no, args.dry_run, args.minimum_free_fee)
        except Exception as exc:
            result = {"originProductNo": origin_no, "updated": False, "reason": str(exc)}
        results.append(result)
        if args.pause_seconds > 0:
            time.sleep(args.pause_seconds)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_json(REPORT_PATH) if REPORT_PATH.exists() else {}
    run = {
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "dryRun": args.dry_run,
        "projectCalculatedOriginsExcluded": not args.include_project_products,
        "results": results,
    }
    history = existing.setdefault("runs", [])
    history.append(run)
    # 마지막 실행 결과는 빠른 점검용으로도 유지한다.
    existing.update(run)
    REPORT_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "targetCount": len(results),
                "updated": sum(item.get("updated") for item in results),
                "unpricedCurrentFeePreserved": sum("wouldSet" in item or item.get("updated") for item in results),
                "failed": [item for item in results if item.get("reason")],
            },
            ensure_ascii=False,
        )
    )
    if not args.dry_run and any(not item.get("updated") for item in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
