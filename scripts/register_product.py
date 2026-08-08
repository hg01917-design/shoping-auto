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
import json
import mimetypes
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers

ROOT = Path(__file__).resolve().parent.parent
STORE_CONFIG_PATH = ROOT / "config" / "store.json"
PRICING_CONFIG_PATH = ROOT / "config" / "pricing.json"

IMAGE_UPLOAD_URL = f"{API_BASE}/v1/product-images/upload"
PRODUCT_URL = f"{API_BASE}/v2/products"

REQUIRED_FIELDS = ("name", "leafCategoryId", "salePrice", "stockQuantity", "detailContent", "images")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_status(product_dir: Path, **updates):
    status_path = product_dir / "status.json"
    status = load_json(status_path) if status_path.exists() else {}
    status.update(updates, updated_at=datetime.now().isoformat())
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sanity_check(listing: dict, pricing_cfg: dict) -> list[str]:
    """등록 불가 사유 목록을 반환한다. 비어 있으면 통과."""
    errors = []
    for field in REQUIRED_FIELDS:
        if not listing.get(field):
            errors.append(f"필수 필드 누락: {field}")

    sale_price = listing.get("salePrice", 0)
    if sale_price and sale_price <= 0:
        errors.append(f"판매가 오류: {sale_price}")

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
        elif rate < target - 0.01:
            errors.append(f"목표마진 미달: {rate:.2%} < {target:.0%}")
        if pricing.get("sale_price") != sale_price:
            errors.append(
                f"listing.salePrice({sale_price})와 pricing.sale_price({pricing.get('sale_price')}) 불일치"
            )

    tags = listing.get("sellerTags", [])
    if len(tags) > 10:
        errors.append(f"sellerTags {len(tags)}개 — 최대 10개")

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


def build_payload(listing: dict, image_urls: list[str], store: dict) -> dict:
    """listing.json + store.json → 커머스API 상품 등록 페이로드"""
    seller_tags = [{"text": t} for t in listing.get("sellerTags", [])[:10]]

    origin_product = {
        "statusType": "SALE",
        "saleType": "NEW",
        "leafCategoryId": str(listing["leafCategoryId"]),
        "name": listing["name"],
        "detailContent": listing["detailContent"],
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
            "deliveryFee": {
                "deliveryFeeType": store.get("delivery_fee_type", "FREE"),
                "baseFee": store.get("base_delivery_fee", 0),
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
            "originAreaInfo": {
                "originAreaCode": store.get("origin_area_code", "0200037"),
                "importer": store.get("importer_name", ""),
            },
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
    pricing_cfg = load_json(PRICING_CONFIG_PATH)
    store = load_json(STORE_CONFIG_PATH)

    errors = sanity_check(listing, pricing_cfg)
    if errors:
        write_status(product_dir, status="error", errors=errors)
        print(f"[!] sanity check 실패 — 등록 스킵:")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    try:
        print(f"[*] 이미지 업로드 중 ({len(listing['images'])}장)...")
        image_urls = upload_images(product_dir, listing["images"])
        print(f"[+] 이미지 업로드 완료: {len(image_urls)}개 URL")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        write_status(product_dir, status="error", errors=[str(e)])
        print(f"[!] {e}")
        sys.exit(1)

    payload = build_payload(listing, image_urls, store)

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
    write_status(product_dir, **result)
    print(f"[+] 등록 성공! productNo={result['productNo']}, originProductNo={result['originProductNo']}")
    return result


def main():
    parser = argparse.ArgumentParser(description="listing.json 기반 스마트스토어 상품 등록")
    parser.add_argument("product_dir", help="상품 폴더 경로 (예: products/kirkland-almond)")
    args = parser.parse_args()
    register(Path(args.product_dir))


if __name__ == "__main__":
    main()
