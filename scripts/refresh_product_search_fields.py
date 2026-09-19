"""등록 상품의 카테고리 속성과 판매 태그를 갱신한다.

사용법:
    python3 scripts/refresh_product_search_fields.py --slug <slug>
    python3 scripts/refresh_product_search_fields.py --force --limit 15
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
REQUEST_INTERVAL_SECONDS = 1.0


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def update_one(product_dir: Path) -> dict:
    status_path = product_dir / "status.json"
    status = load_json(status_path)
    listing = load_json(product_dir / "output" / "listing.json")
    origin_product_no = status.get("originProductNo")
    if status.get("status") != "registered" or not origin_product_no:
        raise ValueError("등록 완료된 상품의 status.json(originProductNo 포함)이 필요합니다.")

    product_url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    current = requests.get(product_url, headers=auth_headers(), timeout=30)
    if current.status_code != 200:
        raise RuntimeError(f"기존 상품 조회 실패 (HTTP {current.status_code}): {current.text[:500]}")
    origin_product = current.json()["originProduct"]
    detail_attribute = origin_product.setdefault("detailAttribute", {})
    detail_attribute["productAttributes"] = listing.get("attributes", [])
    seo_info = detail_attribute.setdefault("seoInfo", {})
    seo_info["sellerTags"] = [{"text": tag} for tag in listing.get("sellerTags", [])[:10]]

    response = requests.put(
        product_url,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json={"originProduct": origin_product},
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"검색 필드 수정 실패 (HTTP {response.status_code}): {response.text[:1200]}")

    status.update(
        {
            "search_fields_updated_at": datetime.now().isoformat(),
            "seller_tag_count": len(listing.get("sellerTags", [])),
            "category_attribute_count": len(listing.get("attributes", [])),
            "updated_at": datetime.now().isoformat(),
        }
    )
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "slug": product_dir.name,
        "seller_tag_count": len(listing.get("sellerTags", [])),
        "attribute_count": len(listing.get("attributes", [])),
    }


def main():
    parser = argparse.ArgumentParser(description="등록 상품 검색 필드 갱신")
    parser.add_argument("--slug", help="특정 상품 slug")
    parser.add_argument("--slugs", nargs="+", help="여러 특정 상품 slug")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--after", help="이 slug 다음부터 처리")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    product_dirs = []
    if args.slug and args.slugs:
        parser.error("--slug와 --slugs는 함께 사용할 수 없습니다.")
    if args.slug:
        product_dirs = [ROOT / "products" / args.slug]
    elif args.slugs:
        product_dirs = [ROOT / "products" / slug for slug in args.slugs]
    else:
        for status_path in sorted((ROOT / "products").glob("*/status.json")):
            product_dir = status_path.parent
            status = load_json(status_path)
            if status.get("status") != "registered":
                continue
            if args.after and product_dir.name <= args.after:
                continue
            if status.get("search_fields_updated_at") and not args.force:
                continue
            product_dirs.append(product_dir)

    successes, failures = [], []
    for product_dir in product_dirs:
        try:
            result = update_one(product_dir)
            successes.append(result)
            print(f"[+] {result['slug']}: 태그 {result['seller_tag_count']}개, 속성 {result['attribute_count']}개", flush=True)
        except Exception as error:
            failure = {"slug": product_dir.name, "error": str(error)}
            failures.append(failure)
            print(f"[!] {failure['slug']}: {failure['error']}", flush=True)
        time.sleep(REQUEST_INTERVAL_SECONDS)
        if args.limit and len(successes) + len(failures) >= args.limit:
            break

    report = {"successes": successes, "failures": failures}
    report_path = ROOT / "output" / "search-fields-refresh-report.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[=] 완료: 성공 {len(successes)}건, 실패 {len(failures)}건 → {report_path}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
