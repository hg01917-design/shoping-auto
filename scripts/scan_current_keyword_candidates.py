"""등록 상품의 현재 상품명을 기준으로 검색광고 연관 키워드를 재수집한다.

기존 keyword-research.json은 보존하고 output/keyword-research-current.json에 쓴다.
상품명 변경은 이 스크립트가 수행하지 않는다.
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from keyword_research import fetch_keywords, to_count


ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def keyword_hints(listing: dict) -> list[str]:
    """검색광고 입력 한도 안의 상품 관련 조합을 최대 다섯 개 만든다."""
    raw = " ".join(
        str(listing.get(key) or "")
        for key in ("name", "brandName", "modelName")
    )
    words = [
        word
        for word in re.findall(r"[가-힣A-Za-z]+", raw)
        if len(word) >= 2 and word.lower() not in {"cm", "ml", "kg", "pcs", "pair"}
    ]
    compact = [word.replace(" ", "") for word in words]
    candidates = []
    for sequence in (compact[:4], list(reversed(compact))[:4]):
        value = ""
        for word in sequence:
            proposed = value + word
            if len(proposed.encode("utf-8")) > 30:
                break
            value = proposed
        if value:
            candidates.append(value)
    candidates.extend(compact)
    seen = set()
    hints = []
    for candidate in candidates:
        if candidate in seen or len(candidate.encode("utf-8")) > 30:
            continue
        seen.add(candidate)
        hints.append(candidate)
        if len(hints) == 5:
            break
    return hints


def candidates_for(hints: list[str]) -> list[dict]:
    records = []
    for item in fetch_keywords(hints):
        pc = to_count(item.get("monthlyPcQcCnt"))
        mobile = to_count(item.get("monthlyMobileQcCnt"))
        total = pc + mobile
        if 50 <= total <= 200:
            records.append(
                {
                    "keyword": item.get("relKeyword"),
                    "monthly_pc_query_count": pc,
                    "monthly_mobile_query_count": mobile,
                    "monthly_query_count": total,
                }
            )
    return sorted(records, key=lambda item: (item["monthly_query_count"], item["keyword"] or ""))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--delay", type=float, default=0.7)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    statuses = sorted((ROOT / "products").glob("*/status.json"))
    completed = 0
    for status_path in statuses:
        status = load_json(status_path)
        if status.get("status") != "registered":
            continue
        listing_path = status_path.parent / "output" / "listing.json"
        if not listing_path.exists():
            continue
        listing = load_json(listing_path)
        name = (listing.get("name") or "").strip()
        hints = keyword_hints(listing)
        if not name or not hints:
            continue
        output_path = status_path.parent / "output" / "keyword-research-current.json"
        if args.skip_existing and output_path.exists():
            continue
        try:
            candidates = candidates_for(hints)
            payload = {
                "source": "NAVER Search Ad API Keyword Tool",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "hint": name,
                "hints": hints,
                "volume_range": {"min": 50, "max": 200},
                "candidates": candidates,
                "decision": "후보의 상품 관련성은 별도 검토가 필요하며 이 파일만으로 상품명을 수정하지 않는다.",
            }
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"OK\t{status_path.parent.name}\t{len(candidates)}")
        except Exception as exc:
            print(f"ERROR\t{status_path.parent.name}\t{exc}")
        completed += 1
        if args.limit is not None and completed >= args.limit:
            break
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
