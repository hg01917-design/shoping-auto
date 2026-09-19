"""등록된 상품의 가공 이미지를 다시 업로드하고 상세페이지를 교체한다.

사용법:
    python3 scripts/refresh_product_images.py products/<slug>

신규 상품을 등록하지 않는다. 기존 원본 상품의 이미지와 detailContent만 갱신한다.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers
from register_product import (
    build_detail_content,
    resolve_processed_image_groups,
    upload_images,
)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def refresh_product_images(product_dir: Path) -> dict:
    """현재 상품의 다른 속성은 보존하고 이미지·상세설명만 갱신한다."""
    status_path = product_dir / "status.json"
    listing_path = product_dir / "output" / "listing.json"
    status = load_json(status_path)
    listing = load_json(listing_path)
    origin_product_no = status.get("originProductNo")
    if status.get("status") != "registered" or not origin_product_no:
        raise ValueError("등록 완료된 상품의 status.json(originProductNo 포함)이 필요합니다.")

    product_url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    get_response = requests.get(product_url, headers=auth_headers(), timeout=30)
    if get_response.status_code != 200:
        raise RuntimeError(f"기존 상품 조회 실패 (HTTP {get_response.status_code}): {get_response.text[:500]}")

    image_groups = resolve_processed_image_groups(product_dir, listing["images"])
    image_paths = [path for group in image_groups for path in group]
    image_urls = upload_images(product_dir, image_paths)
    if not image_urls:
        raise RuntimeError("새 가공 이미지 업로드 결과가 비어 있습니다.")

    origin_product = get_response.json()["originProduct"]
    # listing.json의 이름은 키워드 조사·선정 근거를 거친 현재 상품명이다.
    # 이미지 갱신 때도 이 값을 함께 반영해 상세 설명·이미지·상품명이 어긋나지 않게 한다.
    origin_product["name"] = listing["name"]
    origin_product["images"] = {
        "representativeImage": {"url": image_urls[0]},
        "optionalImages": [{"url": url} for url in image_urls[1:]],
    }
    origin_product["detailContent"] = build_detail_content(
        listing["detailContent"],
        image_urls,
        listing.get("detailKeywords") or listing.get("sellerTags", []),
        [len(group) for group in image_groups],
    )

    put_response = requests.put(
        product_url,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json={"originProduct": origin_product},
        timeout=60,
    )
    if put_response.status_code != 200:
        raise RuntimeError(f"상품 이미지 수정 실패 (HTTP {put_response.status_code}): {put_response.text[:1500]}")

    status.update(
        {
            "images_refreshed_at": datetime.now().isoformat(),
            "detail_updated_at": datetime.now().isoformat(),
            "detail_image_count": len(image_urls),
            "updated_at": datetime.now().isoformat(),
        }
    )
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"slug": product_dir.name, "image_count": len(image_urls)}


def main():
    parser = argparse.ArgumentParser(description="등록 상품의 이미지·상세페이지 갱신")
    parser.add_argument("product_dir", help="상품 폴더 경로")
    args = parser.parse_args()
    result = refresh_product_images(Path(args.product_dir))
    print(f"[+] {result['slug']}: 이미지 {result['image_count']}장 반영")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] {exc}")
        sys.exit(1)
