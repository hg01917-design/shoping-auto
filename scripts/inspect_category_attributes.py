"""네이버 카테고리의 등록 가능 상품 속성을 조회한다.

사용법:
    python3 scripts/inspect_category_attributes.py <leaf-category-id>
"""

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers


def main():
    parser = argparse.ArgumentParser(description="카테고리별 상품 속성 조회")
    parser.add_argument("category_id")
    parser.add_argument("--attribute-seq", type=int, help="선택한 속성의 허용 값까지 조회")
    args = parser.parse_args()
    url = (
        f"{API_BASE}/v1/product-attributes/attribute-values"
        if args.attribute_seq
        else f"{API_BASE}/v1/product-attributes/attributes"
    )
    params = {"categoryId": args.category_id}
    if args.attribute_seq:
        params["attributeSeq"] = args.attribute_seq
    response = requests.get(
        url, headers=auth_headers(), params=params, timeout=30
    )
    if response.status_code != 200:
        raise RuntimeError(f"속성 조회 실패 (HTTP {response.status_code}): {response.text[:1000]}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"[!] {error}", file=sys.stderr)
        sys.exit(1)
