"""등록 완료 상품 전체의 가공 이미지·상세페이지를 순차 갱신한다."""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_product_images import refresh_product_images


ROOT = Path(__file__).resolve().parent.parent
REQUEST_INTERVAL_SECONDS = 1.5


def main():
    parser = argparse.ArgumentParser(description="등록 상품의 이미지·상세페이지를 순차 갱신")
    parser.add_argument("--force", action="store_true", help="기존 갱신 여부와 관계없이 전체 재업로드")
    args = parser.parse_args()
    successes = []
    failures = []
    for status_path in sorted((ROOT / "products").glob("*/status.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") != "registered":
            continue
        product_dir = status_path.parent
        if status.get("images_refreshed_at") and not args.force:
            print(f"[=] {product_dir.name}: 이번 실행에서 이미 반영됨 — 스킵", flush=True)
            continue
        try:
            result = refresh_product_images(product_dir)
            successes.append(result)
            print(f"[+] {result['slug']}: 이미지 {result['image_count']}장 반영", flush=True)
        except Exception as exc:
            failures.append({"slug": product_dir.name, "error": str(exc)})
            print(f"[!] {product_dir.name}: {exc}", flush=True)
        time.sleep(REQUEST_INTERVAL_SECONDS)

    report = {"successes": successes, "failures": failures}
    report_path = ROOT / "output" / "image-refresh-report.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[=] 완료: 성공 {len(successes)}건, 실패 {len(failures)}건 → {report_path}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
