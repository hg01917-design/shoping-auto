"""MYBOX 원본명으로 코스트코 코리아 현재 판매 후보를 수집한다.

자동 매칭·자동 가격 확정 도구가 아니다. 과거 원본의 맛·용량·입수와 현재 상품을
대조할 때 사용할 공식 상품명·링크 후보만 기록한다.

사용법:
  python3 scripts/research_mybox_current_candidates.py --prefix '700 커피 및 음료' --limit 40
"""

import argparse
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "research" / "mybox-400-import.json"
OUTPUT = ROOT / "research" / "mybox-current-search-candidates.json"
BASE_URL = "https://www.costco.co.kr"
KST = timezone(timedelta(hours=9))


def query_from_folder(source_folder: str) -> str:
    name = source_folder.rsplit("/", 1)[-1]
    name = re.sub(r"^\d+\s*", "", name)
    return re.sub(r"\s+", " ", name).strip()


def parse_candidates(page: str) -> list[dict]:
    pattern = re.compile(
        r'<a[^>]+class="thumb"[^>]+title="([^"]+)"[^>]+href="([^"]+)"', re.S
    )
    results = []
    seen = set()
    for title, href in pattern.findall(page):
        title = html.unescape(title).strip()
        href = html.unescape(href).strip()
        if not title or href in seen:
            continue
        seen.add(href)
        results.append({"title": title, "url": BASE_URL + href})
    return results


def fetch(record: dict) -> dict:
    query = query_from_folder(record["source_folder"])
    try:
        response = requests.get(
            BASE_URL + "/search",
            params={"text": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; MYBOX-product-review/1.0)"},
            timeout=30,
        )
        response.raise_for_status()
        return {
            "id": record["id"],
            "source_folder": record["source_folder"],
            "query": query,
            "http_status": response.status_code,
            "candidates": parse_candidates(response.text)[:15],
        }
    except requests.RequestException as error:
        return {
            "id": record["id"],
            "source_folder": record["source_folder"],
            "query": query,
            "error": str(error),
            "candidates": [],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="MYBOX→코스트코 현재 상품 후보 수집")
    parser.add_argument("--prefix", help="source_folder 접두어로 범위 제한")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    records = json.loads(MANIFEST.read_text(encoding="utf-8"))["records"]
    targets = [
        record
        for record in records
        if record.get("review_status") == "official_price_unconfirmed"
        and (not args.prefix or record["source_folder"].startswith(args.prefix))
    ][: args.limit]

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4))) as pool:
        results = list(pool.map(fetch, targets))

    payload = {
        "generated_at": datetime.now(KST).isoformat(),
        "scope_prefix": args.prefix,
        "target_count": len(targets),
        "results": results,
        "note": "후보 링크는 원본 라벨의 브랜드·맛·용량·입수와 대조한 뒤에만 현재가 확인·등록에 사용할 수 있습니다.",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    matched = sum(bool(item["candidates"]) for item in results)
    print(f"[+] {len(targets)}개 조회, 후보 있음 {matched}개 → {OUTPUT}")


if __name__ == "__main__":
    main()
