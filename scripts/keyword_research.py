"""네이버 검색광고 키워드 도구로 연관 검색어의 월간 검색량을 조회한다.

사용법:
  python3 scripts/keyword_research.py "그릭요거트,무지방요거트" \
    --output products/<slug>/output/keyword-research.json
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests


ROOT = Path(__file__).resolve().parent.parent
ENV_PATHS = (
    ROOT / ".env",
    Path(os.environ.get("HOME", "")) / "Downloads" / ".env",
)
API_BASE = "https://api.searchad.naver.com"
KEYWORD_TOOL_URI = "/keywordstool"


def load_searchad_credentials() -> dict:
    """.env에서 검색광고 API에 필요한 값만 읽고, 값은 출력하지 않는다."""
    keys = {"NAVER_API_KEY", "NAVER_SECRET_KEY", "NAVER_CUSTOMER_ID"}
    for path in ENV_PATHS:
        if not path.exists():
            continue
        values = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in keys:
                values[key] = value.strip().strip('"').strip("'")
        if keys.issubset(values) and all(values[key] for key in keys):
            return values
    raise FileNotFoundError(
        ".env에 NAVER_API_KEY, NAVER_SECRET_KEY, NAVER_CUSTOMER_ID가 필요합니다."
    )


def make_signature(secret_key: str, timestamp: str, method: str, uri: str) -> str:
    message = f"{timestamp}.{method}.{uri}".encode("utf-8")
    digest = hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def to_count(value) -> int:
    """'< 10'처럼 정확한 수치가 아닌 값은 0으로 처리해 후보에서 제외한다."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def fetch_keywords(hints: list[str]) -> list[dict]:
    credentials = load_searchad_credentials()
    timestamp = str(int(time.time() * 1000))
    query = urlencode({"hintKeywords": ",".join(hints), "showDetail": "1"})
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": credentials["NAVER_API_KEY"],
        "X-Customer": credentials["NAVER_CUSTOMER_ID"],
        "X-Signature": make_signature(
            credentials["NAVER_SECRET_KEY"], timestamp, "GET", KEYWORD_TOOL_URI
        ),
    }
    response = requests.get(
        f"{API_BASE}{KEYWORD_TOOL_URI}?{query}", headers=headers, timeout=30
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"네이버 검색광고 키워드 조회 실패 (HTTP {response.status_code}): "
            f"{response.text[:500]}"
        )
    return response.json().get("keywordList", [])


def main():
    parser = argparse.ArgumentParser(description="네이버 연관 검색어 검색량 조회")
    parser.add_argument("hints", help="쉼표로 구분한 상품 관련 키워드")
    parser.add_argument("--min-volume", type=int, default=50)
    parser.add_argument("--max-volume", type=int, default=200)
    parser.add_argument("--output", required=True, help="검색 근거 JSON 저장 경로")
    args = parser.parse_args()

    if args.min_volume < 0 or args.min_volume > args.max_volume:
        parser.error("검색량 범위가 올바르지 않습니다.")

    hints = [hint.strip() for hint in args.hints.split(",") if hint.strip()]
    if not hints:
        parser.error("검색 키워드를 하나 이상 입력하세요.")

    records = []
    for item in fetch_keywords(hints):
        pc = to_count(item.get("monthlyPcQcCnt"))
        mobile = to_count(item.get("monthlyMobileQcCnt"))
        total = pc + mobile
        if args.min_volume <= total <= args.max_volume:
            records.append(
                {
                    "keyword": item.get("relKeyword"),
                    "monthly_pc_query_count": pc,
                    "monthly_mobile_query_count": mobile,
                    "monthly_query_count": total,
                }
            )

    records.sort(key=lambda item: (item["monthly_query_count"], item["keyword"] or ""))
    output = {
        "source": "NAVER Search Ad API Keyword Tool",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "hints": hints,
        "volume_range": {"min": args.min_volume, "max": args.max_volume},
        "candidates": records,
        "note": "후보 중 실제 상품과 직접 관련된 검색어만 상품명에 사용한다.",
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] {len(records)}개 후보 저장 → {output_path}")


if __name__ == "__main__":
    main()
