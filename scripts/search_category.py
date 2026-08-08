# 네이버 커머스API 카테고리 검색 → leafCategoryId 탐색
#   - config/categories.json 캐시 우선 조회
#   - 캐시 미스 시 전체 카테고리 API 조회 후 키워드 매칭, 결과를 캐시에 추가
#
# 사용법:
#   python3 scripts/search_category.py "건강식품"           # 키워드로 리프 카테고리 검색
#   python3 scripts/search_category.py "건강식품" --limit 10
#
# 주의: 카테고리 조회 엔드포인트/응답 스키마는 커머스API 문서 기준
#   GET /external/v1/categories (전체 카테고리 목록)
# 스펙 변경 시 https://apicenter.commerce.naver.com 에서 재확인 필요.

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_auth import API_BASE, auth_headers

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "config" / "categories.json"
CATEGORIES_URL = f"{API_BASE}/v1/categories"


def load_cache() -> dict:
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_all_categories() -> list[dict]:
    resp = requests.get(CATEGORIES_URL, headers=auth_headers(), timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"카테고리 조회 실패 (HTTP {resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    # 응답이 {"categories": [...]} 또는 바로 리스트인 경우 모두 대응
    return data if isinstance(data, list) else data.get("categories", data)


def search(keyword: str, limit: int = 5) -> list[dict]:
    """키워드로 리프 카테고리를 검색한다. 캐시 우선, 미스 시 API 조회 + 캐시 갱신."""
    cache = load_cache()

    hits = [
        {"id": cid, "wholeCategoryName": name}
        for name, cid in cache.items()
        if keyword in name
    ]
    if hits:
        return hits[:limit]

    categories = fetch_all_categories()
    matches = []
    for cat in categories:
        name = cat.get("wholeCategoryName") or cat.get("name", "")
        # last=True 가 리프 카테고리 (필드 없으면 리프로 간주)
        if keyword in name and cat.get("last", True):
            matches.append({"id": str(cat["id"]), "wholeCategoryName": name})

    for m in matches[:limit]:
        cache[m["wholeCategoryName"]] = m["id"]
    if matches:
        save_cache(cache)

    return matches[:limit]


def main():
    parser = argparse.ArgumentParser(description="스마트스토어 리프 카테고리 검색")
    parser.add_argument("keyword", help="카테고리 검색 키워드 (예: 건강식품)")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    results = search(args.keyword, args.limit)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not results:
        print(f"[!] '{args.keyword}' 매칭 카테고리 없음 — 다른 키워드로 재시도하세요.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
