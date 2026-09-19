"""등록 상품의 판매자 태그를 네이버 커머스 API에 반영한다.

사용법:
    python3 scripts/update_seller_tags.py products/<slug> --tag 태그 --tag 태그
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="등록 상품 판매자 태그 변경")
    parser.add_argument("product_dir")
    parser.add_argument("--tag", action="append", required=True)
    args = parser.parse_args()

    tags = list(dict.fromkeys(tag.strip() for tag in args.tag if tag.strip()))
    if not tags or len(tags) > 10:
        raise ValueError("판매자 태그는 중복 없이 1~10개여야 합니다.")

    product_dir = Path(args.product_dir)
    listing_path = product_dir / "output" / "listing.json"
    status_path = product_dir / "status.json"
    listing = load_json(listing_path)
    status = load_json(status_path)
    origin_product_no = status.get("originProductNo")
    if status.get("status") != "registered" or not origin_product_no:
        raise ValueError("등록 완료된 상품의 status.json(originProductNo 포함)이 필요합니다.")

    url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    response = requests.get(url, headers=auth_headers(), timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"기존 상품 조회 실패 (HTTP {response.status_code}): {response.text[:500]}")

    origin_product = response.json()["originProduct"]
    detail_attribute = origin_product.setdefault("detailAttribute", {})
    detail_attribute["seoInfo"] = {"sellerTags": [{"text": tag} for tag in tags]}
    response = requests.put(
        url,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json={"originProduct": origin_product},
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"판매자 태그 수정 실패 (HTTP {response.status_code}): {response.text[:1500]}")

    listing["sellerTags"] = tags
    listing_path.write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")
    status["seller_tags_updated_at"] = datetime.now().isoformat()
    status["sellerTags"] = tags
    status["updated_at"] = datetime.now().isoformat()
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"slug": product_dir.name, "sellerTags": tags}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] {exc}")
        sys.exit(1)
