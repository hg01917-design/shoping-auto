"""등록 상품의 로컬 가공 이미지를 새 레이아웃 규칙으로 다시 만든다.

스마트스토어에는 업로드하지 않는다. 업로드는 refresh_registered_product_images.py가 담당한다.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from process_images import TARGET_SIZE, process_dir


ROOT = Path(__file__).resolve().parent.parent


def main():
    successes, failures = [], []
    for status_path in sorted((ROOT / "products").glob("*/status.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") != "registered":
            continue
        product_dir = status_path.parent
        try:
            results = process_dir(product_dir / "input" / "images", product_dir / "output" / "images", TARGET_SIZE)
            failed = [result for result in results if result.get("error")]
            if failed:
                raise RuntimeError("; ".join(item["error"] for item in failed))
            manifest_path = product_dir / "output" / "images" / "processing-manifest.json"
            manifest_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            status["images_reprocessed_at"] = datetime.now().isoformat()
            status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
            successes.append(product_dir.name)
            print(f"[+] {product_dir.name}: {len(results)}개 원본 재가공", flush=True)
        except Exception as exc:
            failures.append({"slug": product_dir.name, "error": str(exc)})
            print(f"[!] {product_dir.name}: {exc}", flush=True)
    print(f"[=] 완료: 성공 {len(successes)}건, 실패 {len(failures)}건")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
