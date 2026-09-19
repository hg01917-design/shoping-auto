"""현재 검색량 조사에서 라벨·소스 문구와 직접 겹치는 후보만 추린다.

자동 제목 변경은 수행하지 않는다. 사람이 제품 사실·문장 자연스러움을 최종 확인한다.
"""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


for status_path in sorted((ROOT / "products").glob("*/status.json")):
    status = load(status_path)
    product_dir = status_path.parent
    listing_path = product_dir / "output" / "listing.json"
    research_path = product_dir / "output" / "keyword-research-current.json"
    source_path = product_dir / "input" / "source.md"
    if status.get("status") != "registered" or not listing_path.exists() or not research_path.exists():
        continue
    listing = load(listing_path)
    research = load(research_path)
    source = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    evidence = normalize(" ".join([listing.get("name", ""), listing.get("modelName", ""), source]))
    matches = []
    for candidate in research.get("candidates", []):
        keyword = candidate.get("keyword") or ""
        compact = normalize(keyword)
        if len(compact) >= 4 and compact in evidence:
            matches.append(candidate)
    name_compact = normalize(listing.get("name", ""))
    print(json.dumps({
        "slug": product_dir.name,
        "name": listing.get("name"),
        "matches": matches[:12],
        "starts_with_matched_candidate": any(
            name_compact.startswith(normalize(item.get("keyword") or ""))
            for item in matches
        ),
    }, ensure_ascii=False))
