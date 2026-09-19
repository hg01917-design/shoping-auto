"""등록된 스마트스토어 상품의 제목만 안전하게 교체한다.

이미지·가격·고시·상세설명은 변경하지 않는다.
사용법:
  python3 scripts/update_registered_product_titles.py
  python3 scripts/update_registered_product_titles.py products/<slug>
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def update(product_dir: Path, force: bool = False) -> dict:
    status_path = product_dir / "status.json"
    listing_path = product_dir / "output" / "listing.json"
    status, listing = load(status_path), load(listing_path)
    product_no = status.get("originProductNo")
    if status.get("status") != "registered" or not product_no:
        raise ValueError("등록 완료 상태와 originProductNo가 필요합니다.")
    if status.get("title_updated_at") and not force:
        return {"slug": product_dir.name, "result": "skipped"}

    url = f"{API_BASE}/v2/products/origin-products/{product_no}"
    response = requests.get(url, headers=auth_headers(), timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"기존 상품 조회 실패 (HTTP {response.status_code}): {response.text[:500]}")
    origin_product = response.json()["originProduct"]
    previous_name = origin_product.get("name", "")
    origin_product["name"] = listing["name"]
    if previous_name != listing["name"]:
        response = requests.put(
            url,
            headers={**auth_headers(), "Content-Type": "application/json"},
            json={"originProduct": origin_product},
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(f"상품명 수정 실패 (HTTP {response.status_code}): {response.text[:1200]}")
    public_product_no = status.get("productNo")
    if public_product_no:
        status["publicProductUrl"] = (
            f"https://smartstore.naver.com/main/products/{public_product_no}"
        )
    status.update({
        "title_updated_at": datetime.now().isoformat(),
        "title_updated_from": previous_name,
        "title_updated_to": listing["name"],
        "updated_at": datetime.now().isoformat(),
    })
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"slug": product_dir.name, "result": "updated", "from": previous_name, "to": listing["name"]}


def main():
    parser = argparse.ArgumentParser(description="등록 상품의 제목만 순차 수정")
    parser.add_argument("product_dirs", nargs="*", help="비우면 제목 미수정 등록 상품 전체")
    parser.add_argument("--force", action="store_true", help="이전에 제목을 수정한 등록 상품도 다시 반영")
    args = parser.parse_args()
    targets = [Path(item) for item in args.product_dirs] if args.product_dirs else [
        path.parent for path in sorted((ROOT / "products").glob("*/status.json"))
    ]
    results = []
    for product_dir in targets:
        status = load(product_dir / "status.json")
        if status.get("status") != "registered" or (status.get("title_updated_at") and not args.force):
            continue
        results.append(update(product_dir, force=args.force))
        time.sleep(0.7)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] {exc}")
        raise SystemExit(1)
