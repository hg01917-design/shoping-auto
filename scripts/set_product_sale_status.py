"""등록 상품의 스마트스토어 판매 상태를 변경한다.

사용법:
    python3 scripts/set_product_sale_status.py products/<slug> --status SUSPENSION --reason "사유"
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


def change_status(product_dir: Path, status_type: str, reason: str) -> None:
    status_path = product_dir / "status.json"
    status = load_json(status_path)
    origin_product_no = status.get("originProductNo")
    if status.get("status") != "registered" or not origin_product_no:
        raise ValueError(f"{product_dir.name}: 등록 완료 상품의 originProductNo가 필요합니다.")

    url = f"{API_BASE}/v2/products/origin-products/{origin_product_no}"
    response = requests.get(url, headers=auth_headers(), timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"{product_dir.name}: 상품 조회 실패 (HTTP {response.status_code}): {response.text[:500]}"
        )
    origin_product = response.json()["originProduct"]
    previous = origin_product.get("statusType")
    if previous != status_type:
        origin_product["statusType"] = status_type
        response = requests.put(
            url,
            headers={**auth_headers(), "Content-Type": "application/json"},
            json={"originProduct": origin_product},
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"{product_dir.name}: 판매 상태 변경 실패 (HTTP {response.status_code}): {response.text[:1500]}"
            )

    now = datetime.now().isoformat()
    status["remote_sale_status"] = status_type
    status["sale_status_changed_at"] = now
    status["sale_status_reason"] = reason
    status["updated_at"] = now
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] {product_dir.name}: {previous} -> {status_type}")


def main() -> None:
    parser = argparse.ArgumentParser(description="등록 상품의 스마트스토어 판매 상태 변경")
    parser.add_argument("product_dirs", nargs="+", help="상품 폴더 경로")
    parser.add_argument("--status", choices=("SALE", "SUSPENSION"), required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    for product_dir in args.product_dirs:
        change_status(Path(product_dir), args.status, args.reason)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] {exc}")
        sys.exit(1)
