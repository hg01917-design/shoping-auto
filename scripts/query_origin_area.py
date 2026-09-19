"""네이버 커머스API에서 원산지 상세 지역명으로 원산지 코드를 조회한다.

사용법:
  python3 scripts/query_origin_area.py "대한민국"
"""

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers


def main():
    parser = argparse.ArgumentParser(description="네이버 원산지 코드 조회")
    parser.add_argument("origin_area_name", help="원산지 상세 지역명 (예: 대한민국, 미국)")
    args = parser.parse_args()

    response = requests.get(
        f"{API_BASE}/v1/product-origin-areas/query",
        headers=auth_headers(),
        params={"name": args.origin_area_name},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"원산지 코드 조회 실패 (HTTP {response.status_code}): {response.text[:500]}"
        )
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
