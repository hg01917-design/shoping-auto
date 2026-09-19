"""등록된 스마트스토어 상품의 상세설명에 상품 이미지를 반영한다.

사용법:
    python3 scripts/update_product_detail.py products/<product-slug>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers
from register_product import build_detail_content

STORE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "store.json"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def image_urls(images: dict) -> list[str]:
    urls = []
    representative = images.get("representativeImage", {}).get("url")
    if representative:
        urls.append(representative)
    urls.extend(
        image.get("url")
        for image in images.get("optionalImages", [])
        if image.get("url")
    )
    return urls


def update_detail(product_dir: Path) -> None:
    status_path = product_dir / "status.json"
    listing_path = product_dir / "output" / "listing.json"
    status = load_json(status_path)
    listing = load_json(listing_path)
    origin_product_no = status.get("originProductNo")
    if status.get("status") != "registered" or not origin_product_no:
        raise ValueError("등록 완료된 상품의 status.json(originProductNo 포함)이 필요합니다.")

    url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    response = requests.get(url, headers=auth_headers(), timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"기존 상품 조회 실패 (HTTP {response.status_code}): {response.text[:500]}")

    origin_product = response.json()["originProduct"]
    urls = image_urls(origin_product.get("images", {}))
    if not urls:
        raise RuntimeError("등록된 상품에서 상세페이지에 사용할 이미지 URL을 찾지 못했습니다.")

    origin_product["detailContent"] = build_detail_content(
        listing["detailContent"],
        urls,
        listing.get("detailKeywords") or listing.get("sellerTags", []),
    )
    if listing.get("leafCategoryId"):
        origin_product["leafCategoryId"] = str(listing["leafCategoryId"])
    if listing.get("salePrice"):
        origin_product["salePrice"] = listing["salePrice"]
    if listing.get("originAreaInfo"):
        origin_product["detailAttribute"]["originAreaInfo"] = listing["originAreaInfo"]
    store = load_json(STORE_CONFIG_PATH)
    delivery_fee = origin_product.setdefault("deliveryInfo", {}).setdefault("deliveryFee", {})
    customer_delivery_fee = listing.get(
        "customerDeliveryFee",
        listing.get("pricing", {}).get(
            "customer_delivery_fee", store.get("base_delivery_fee", 3000)
        ),
    )
    delivery_fee.update(
        {
            "deliveryFeeType": store.get("delivery_fee_type", "UNIT_QUANTITY_PAID"),
            "baseFee": customer_delivery_fee,
            "deliveryFeePayType": store.get("delivery_fee_pay_type", "PREPAID"),
        }
    )
    if delivery_fee["deliveryFeeType"] == "UNIT_QUANTITY_PAID":
        delivery_fee["repeatQuantity"] = store.get("delivery_fee_repeat_quantity", 1)
    origin_product["deliveryInfo"]["deliveryBundleGroupUsable"] = store.get(
        "delivery_bundle_group_usable", False
    )
    claim_delivery = origin_product["deliveryInfo"].setdefault("claimDeliveryInfo", {})
    claim_delivery.update(
        {
            "returnDeliveryFee": store.get("return_delivery_fee", 6000),
            "exchangeDeliveryFee": store.get("exchange_delivery_fee", 6000),
        }
    )
    response = requests.put(
        url,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json={"originProduct": origin_product},
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"상세페이지 수정 실패 (HTTP {response.status_code}): {response.text[:1500]}")

    status["detail_updated_at"] = datetime.now().isoformat()
    status["detail_image_count"] = len(urls)
    if listing.get("leafCategoryId"):
        status["leafCategoryId"] = str(listing["leafCategoryId"])
    if listing.get("salePrice"):
        status["salePrice"] = listing["salePrice"]
    status["customerDeliveryFee"] = customer_delivery_fee
    status["updated_at"] = datetime.now().isoformat()
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] 상세페이지 수정 성공: 이미지 {len(urls)}장 반영")


def main():
    parser = argparse.ArgumentParser(description="등록 상품 상세페이지에 이미지 반영")
    parser.add_argument("product_dir", help="상품 폴더 경로")
    args = parser.parse_args()
    update_detail(Path(args.product_dir))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] {exc}")
        sys.exit(1)
