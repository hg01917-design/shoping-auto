"""네이버 검색광고 키워드 근거로 listing 상품명·상세 키워드를 재정리한다.

사용법:
    python3 scripts/rebuild_product_titles.py --apply
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from keyword_research import fetch_keywords, to_count


ROOT = Path(__file__).resolve().parent.parent
MIN_VOLUME = 50
MAX_VOLUME = 200


def normalize(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", value.lower())


def source_title(product_dir: Path) -> str:
    source = (product_dir / "input" / "source.md").read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return ""


def fetch_candidates(hint: str) -> list[dict]:
    candidates = []
    for item in fetch_keywords([hint]):
        pc = to_count(item.get("monthlyPcQcCnt"))
        mobile = to_count(item.get("monthlyMobileQcCnt"))
        total = pc + mobile
        if MIN_VOLUME <= total <= MAX_VOLUME and item.get("relKeyword"):
            candidates.append(
                {
                    "keyword": item["relKeyword"],
                    "monthly_pc_query_count": pc,
                    "monthly_mobile_query_count": mobile,
                    "monthly_query_count": total,
                }
            )
    return sorted(candidates, key=lambda item: (item["monthly_query_count"], item["keyword"]))


def selected_keywords(listing: dict, research: dict, source_text: str) -> list[dict]:
    known = list(listing.get("sellerTags", [])) + [listing.get("name", ""), source_text]
    known_normalized = [normalize(value) for value in known if value]
    candidates = research.get("candidates", [])
    selected = []
    for candidate in candidates:
        keyword = candidate.get("keyword", "")
        normalized = normalize(keyword)
        # 실제 원본/판매 태그에 있는 직접 연관어만 자동 선택한다.
        if normalized and any(normalized in value for value in known_normalized):
            selected.append(
                {
                    "keyword": keyword,
                    "monthly_query_count": candidate["monthly_query_count"],
                    "reason": "원본 상품 정보 또는 판매 태그와 직접 일치",
                }
            )
    selected.sort(key=lambda item: (item["monthly_query_count"], item["keyword"]))
    unique = []
    for item in selected:
        if item["keyword"] not in [chosen["keyword"] for chosen in unique]:
            unique.append(item)
        if len(unique) == 2:
            break
    return unique


def rebuild_product(product_dir: Path, apply: bool) -> dict:
    listing_path = product_dir / "output" / "listing.json"
    research_path = product_dir / "output" / "keyword-research.json"
    listing = json.loads(listing_path.read_text(encoding="utf-8"))
    source_name = source_title(product_dir)
    research = json.loads(research_path.read_text(encoding="utf-8")) if research_path.exists() else {}

    # 근거가 없는 상품만 직접 연관 판매 태그 하나로 새 조회한다.
    if not research.get("candidates"):
        hint = next((tag for tag in listing.get("sellerTags", []) if tag), "")
        if hint:
            research = {
                "source": "NAVER Search Ad API Keyword Tool",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "hints": [hint],
                "volume_range": {"min": MIN_VOLUME, "max": MAX_VOLUME},
                "candidates": fetch_candidates(hint),
            }
            time.sleep(0.8)

    selected = selected_keywords(listing, research, source_name)
    base = " ".join(value for value in [listing.get("brandName", ""), listing.get("modelName", "")] if value).strip()
    if not base:
        base = source_name or listing["name"]
    name = " ".join([item["keyword"] for item in selected] + [base]).strip()[:100]
    research.update(
        {
            "selected": selected,
            "excluded": [],
            "title": name,
            "title_rebuilt_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if apply:
        listing["name"] = name
        listing["detailKeywords"] = [item["keyword"] for item in selected]
        listing_path.write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")
        research_path.write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"slug": product_dir.name, "name": name, "selected": selected}


def main():
    parser = argparse.ArgumentParser(description="상품명 키워드 근거 재정리")
    parser.add_argument("--apply", action="store_true", help="listing.json과 근거 파일에 저장")
    args = parser.parse_args()
    results = []
    for status_path in sorted((ROOT / "products").glob("*/status.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") == "registered":
            results.append(rebuild_product(status_path.parent, args.apply))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
