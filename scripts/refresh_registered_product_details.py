"""등록 상품의 이미지 URL은 유지한 채 상세페이지 문구만 다시 반영한다.

사용법:
    python3 scripts/refresh_registered_product_details.py --force
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
from detail_quality import audit_listing, repair_listing
from register_product import build_detail_content, resolve_processed_image_groups


ROOT = Path(__file__).resolve().parent.parent
REQUEST_INTERVAL_SECONDS = 1.0


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def existing_image_urls(origin_product: dict) -> list[str]:
    images = origin_product.get("images", {})
    representative = images.get("representativeImage", {}).get("url")
    optional = [item.get("url") for item in images.get("optionalImages", []) if item.get("url")]
    if not representative:
        raise ValueError("기존 대표 이미지 URL을 찾지 못했습니다.")
    return [representative, *optional]


def refresh_product_detail(product_dir: Path) -> dict:
    status_path = product_dir / "status.json"
    listing_path = product_dir / "output" / "listing.json"
    status = load_json(status_path)
    listing = load_json(listing_path)
    listing, repairs = repair_listing(listing)
    if repairs:
        listing_path.write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")
    quality_errors = audit_listing(listing)
    if quality_errors:
        raise ValueError("상세 품질 기준 미달: " + "; ".join(quality_errors))
    origin_product_no = status.get("originProductNo")
    if status.get("status") != "registered" or not origin_product_no:
        raise ValueError("등록 완료된 상품의 status.json(originProductNo 포함)이 필요합니다.")

    product_url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    get_response = requests.get(product_url, headers=auth_headers(), timeout=30)
    if get_response.status_code != 200:
        raise RuntimeError(f"기존 상품 조회 실패 (HTTP {get_response.status_code}): {get_response.text[:500]}")
    origin_product = get_response.json()["originProduct"]
    image_urls = existing_image_urls(origin_product)
    image_groups = resolve_processed_image_groups(product_dir, listing["images"])
    expected_count = sum(len(group) for group in image_groups)
    if len(image_urls) != expected_count:
        raise ValueError(
            f"기존 이미지 {len(image_urls)}장과 현재 가공 구성 {expected_count}장이 달라 "
            "상세 문구만 갱신할 수 없습니다. 먼저 이미지 갱신이 필요합니다."
        )

    origin_product["name"] = listing["name"]
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
        raise RuntimeError(f"상세페이지 수정 실패 (HTTP {put_response.status_code}): {put_response.text[:1200]}")

    status["detail_updated_at"] = datetime.now().isoformat()
    status["updated_at"] = datetime.now().isoformat()
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"slug": product_dir.name, "image_count": len(image_urls)}


def main():
    parser = argparse.ArgumentParser(description="등록 상품 상세페이지 문구 전체 갱신")
    parser.add_argument("--force", action="store_true", help="기존 갱신 시각과 관계없이 전체 적용")
    parser.add_argument("--after", help="이 slug 다음 상품부터 처리 (재개용)")
    parser.add_argument("--limit", type=int, help="이번 실행의 최대 처리 건수")
    parser.add_argument("--slug", help="특정 상품 slug 하나만 상세 문구 갱신")
    parser.add_argument("--slugs", nargs="+", help="여러 특정 상품 slug의 상세 문구 갱신")
    args = parser.parse_args()
    if args.slug and args.slugs:
        parser.error("--slug와 --slugs는 함께 사용할 수 없습니다.")
    requested = set(args.slugs or ([args.slug] if args.slug else []))
    successes, failures = [], []
    for status_path in sorted((ROOT / "products").glob("*/status.json")):
        status = load_json(status_path)
        if status.get("status") != "registered":
            continue
        if requested and status_path.parent.name not in requested:
            continue
        if args.after and status_path.parent.name <= args.after:
            continue
        if status.get("detail_updated_at") and not args.force:
            continue
        try:
            result = refresh_product_detail(status_path.parent)
            successes.append(result)
            print(f"[+] {result['slug']}: 상세 문구 반영", flush=True)
        except Exception as exc:
            failure = {"slug": status_path.parent.name, "error": str(exc)}
            failures.append(failure)
            print(f"[!] {failure['slug']}: {failure['error']}", flush=True)
        time.sleep(REQUEST_INTERVAL_SECONDS)
        if args.limit and len(successes) + len(failures) >= args.limit:
            break

    report = {"successes": successes, "failures": failures}
    report_path = ROOT / "output" / "detail-content-refresh-report.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[=] 완료: 성공 {len(successes)}건, 실패 {len(failures)}건 → {report_path}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
