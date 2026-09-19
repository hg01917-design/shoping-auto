"""네이버 커머스API의 상품정보제공고시 상품군을 조회한다."""

import json
import sys

import requests

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from naver_auth import API_BASE, auth_headers


def main():
    response = requests.get(
        f"{API_BASE}/v1/products-for-provided-notice",
        headers=auth_headers(),
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"고시 상품군 조회 실패 (HTTP {response.status_code}): {response.text[:500]}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
