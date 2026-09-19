"""스마트스토어센터 검색 순위 진단의 확인값을 상품별 이력으로 저장한다.

입력값은 화면에서 직접 확인한 값만 넣는다. 순위가 없는 상품은 추정값 대신
`not_ranked_in_top_200`으로 기록한다.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECKED_AT = "2026-08-18T01:00:00+00:00"
SOURCE = "스마트스토어센터 검색 순위 진단"
CONDITION = "다온나상점 판매중 상품 · 2026-08-17 기준 · 키워드 순위 상위 200위 내 표시값"

# 상품별 키워드: (검색어, 순위, 상태, 증감). 빈 배열은 해당 상품의 키워드가
# 상위 200위 안에 없어서 센터가 순위를 제공하지 않은 경우다.
RANKS = {
    "kirkland-ruby-red-grapefruit-juice-284l-x2": [],
    "kirkland-mineral-water-500ml-x40-x4": [
        ("커클랜드생수500ml", 51, "same", 0),
        ("커클랜드생수", 113, "up", 4),
    ],
    "kirkland-food-wrap-30cm-x914m": [("커클랜드랩", 92, "new", None)],
    "haagen-dazs-vanilla-189l": [
        ("하겐다즈업소용", 75, "new", None),
        ("하겐다즈바닐라", 73, "same", 0),
    ],
    "kirkland-pink-salt-chips-907g": [("커클랜드감자칩", 84, "down", 1)],
    "saputo-cheeseheads-string-cheese-136kg": [],
    "kirkland-pecans-908g": [],
    "kirkland-premium-tissue-40m-x30": [
        ("커클랜드휴지", 115, "down", 2),
        ("커클랜드화장지", 114, "down", 2),
        ("컬크랜드휴지", 126, "new", None),
        ("커틀랜드휴지", None, "out", None),
    ],
    "kirkland-siurana-evoo-1l": [("커클랜드올리브유", 69, "down", 2)],
    "kirkland-crumbles-bacon-567g": [
        ("커클랜드베이컨", 61, "up", 9),
        ("베이컨크럼블", 59, "new", None),
    ],
    "kirkland-dried-blueberries-567g": [],
    "martinellis-apple-juice-296ml-x24": [],
    "starbucks-breakfast-blend-113kg": [
        ("스타벅스홀빈1.13kg", 198, "new", None),
        ("스타벅스원두홀빈1.13kg", None, "out", None),
    ],
    "kirkland-fabric-softener-sheets-250ct-x2": [("커클랜드건조기시트", 69, "down", 1)],
    "kirkland-unsalted-cashews-113kg": [],
    "kirkland-wildflower-honey-227kg": [("커클랜드유기농설탕", 118, "up", 4)],
    "brookfarm-essential-granola-1kg": [],
    "kirkland-mineral-water-2l-x6-x6": [
        ("커클랜드생수", 114, "up", 4),
        ("커클랜드생수2리터", None, "out", None),
    ],
    "kirkland-maple-syrup-1l": [],
    "chosen-foods-avocado-oil-1l": [
        ("초슨푸드아보카도오일", 65, "same", 0),
        ("초슨푸드아보카도유", 63, "new", None),
    ],
    "kirkland-microwave-popcorn-41kg": [("커클랜드팝콘", 79, "same", 0)],
    "kirkland-espresso-whole-bean-113kg": [
        ("커클랜드원두", 176, "new", None),
        ("커클랜드시그니처커피", 94, "new", None),
    ],
    "kirkland-3-piece-golf-ball-24": [
        ("커클랜드골프공", 184, "down", 5),
        ("커클랜드골프공v3.5", 165, "same", 0),
    ],
    "sensodyne-multicare-100g-x5": [("치약센소다인", 155, "new", None)],
    "kirkland-organic-salsa-108kg-x2": [],
    "kirkland-black-pepper-grinder-357g": [],
    "kirkland-roasted-macadamias-680g": [],
}


def main():
    saved = 0
    for slug, values in RANKS.items():
        product_dir = ROOT / "products" / slug
        listing = json.loads((product_dir / "output" / "listing.json").read_text(encoding="utf-8"))
        path = product_dir / "output" / "rank-history.json"
        prior = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"checks": []}
        checks = prior.setdefault("checks", [])
        if any(check.get("checked_at") == CHECKED_AT for check in checks):
            continue
        checks.append({
            "checked_at": CHECKED_AT,
            "source": SOURCE,
            "condition": CONDITION,
            "product_name": listing["name"],
            "keywords": [
                {"keyword": keyword, "rank": rank, "status": status, "delta": delta}
                for keyword, rank, status, delta in values
            ],
            "not_ranked_in_top_200": not values,
        })
        prior["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(prior, ensure_ascii=False, indent=2), encoding="utf-8")
        saved += 1
    print(json.dumps({"saved": saved, "products": len(RANKS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
