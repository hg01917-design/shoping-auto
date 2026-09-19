"""등록 상품의 키워드 근거와 자연스러운 상품명을 준비한다.

각 상품은 일반 상품어 하나로 네이버 검색광고 키워드 도구를 조회한다.
50~200 구간 후보 중, 상품의 브랜드·형태·구성에 모두 맞는 후보만 근거로 남긴다.
원문을 번역하는 대신 검증된 속성을 앞에, 일반 상품어를 한 번만 뒤에 둔다.
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from keyword_research import fetch_keywords, to_count


ROOT = Path(__file__).resolve().parent.parent
MIN_VOLUME, MAX_VOLUME = 50, 200

# title의 마지막 일반 상품어는 한 번만 쓴다. terms는 API 후보가 실제 이 상품과
# 직접 관련됐는지 가르는 사실 키워드이며, 하나만 있는 경우에도 단순 일반어 후보는 채택하지 않는다.
PLANS = {
    "brookfarm-essential-granola-1kg": ("그래놀라", "귀리 그래놀라 브룩팜 에센셜 1kg", ["귀리", "그래놀라"]),
    "cetaphil-moisturizing-lotion-591ml-x2": ("보습로션", "보습로션 세타필 591ml 2개", ["세타필", "로션"]),
    "chosen-foods-avocado-oil-1l": ("아보카도오일", "식용 아보카도오일 초슨푸드 1L", ["초슨", "아보카도"]),
    "colgate-great-regular-250g-x5": ("치약", "대용량 콜게이트 레귤러 치약 250g 5개", ["콜게이트", "치약"]),
    "ediya-special-gold-11g-x400": ("커피믹스", "커피믹스 이디야 골드블렌드 11g 400개", ["이디야", "커피"]),
    "haagen-dazs-vanilla-189l": ("아이스크림", "대용량 바닐라 아이스크림 하겐다즈 1.89L", ["바닐라", "아이스크림"]),
    "kirkland-3-piece-golf-ball-24": ("골프공", "3피스 24개입 커클랜드 시그니처 골프공", ["커클랜드", "골프"]),
    "kirkland-aa-alkaline-battery-48": ("건전지", "알카라인 AA 건전지 커클랜드 시그니처 48개", ["커클랜드", "aa"]),
    "kirkland-aaa-alkaline-battery-48": ("건전지", "알카라인 AAA 건전지 커클랜드 시그니처 48개", ["커클랜드", "aaa"]),
    "kirkland-almonds-136kg": ("아몬드", "생아몬드 대용량 커클랜드 시그니처 1.36kg", ["생", "아몬드"]),
    "kirkland-black-pepper-grinder-357g": ("통후추", "그라인더 통후추 커클랜드 시그니처 357g", ["후추", "그라인더"]),
    "kirkland-cat-food-113kg": ("고양이사료", "건식 고양이사료 커클랜드 시그니처 11.3kg", ["고양이", "사료"]),
    "kirkland-citrus-body-wash-800ml-x2": ("바디워시", "시트러스 바디워시 커클랜드 시그니처 800ml 2개", ["시트러스", "바디"]),
    "kirkland-crumbles-bacon-567g": ("베이컨", "크럼블 베이컨 커클랜드 시그니처 567g", ["크럼블", "베이컨"]),
    "kirkland-dried-blueberries-567g": ("건블루베리", "건블루베리 간식 커클랜드 시그니처 567g", ["블루베리"]),
    "kirkland-dried-plums-158kg": ("건자두", "대용량 건자두 커클랜드 시그니처 1.58kg", ["건", "자두"]),
    "kirkland-espresso-whole-bean-113kg": ("원두", "다크로스팅 에스프레소 원두 커클랜드 시그니처 1.13kg", ["에스프레소", "원두"]),
    "kirkland-fabric-softener-sheets-250ct-x2": ("건조기시트", "리프레싱향 건조기시트 커클랜드 시그니처 250매 2개", ["건조기", "시트"]),
    "kirkland-food-wrap-30cm-x231m-x2": ("주방랩", "대용량 주방랩 커클랜드 시그니처 30cm 231m 2개", ["주방", "랩"]),
    "kirkland-food-wrap-30cm-x914m": ("주방랩", "대용량 주방랩 커클랜드 시그니처 30cm 914m", ["주방", "랩"]),
    "kirkland-greek-yogurt-907g-x2": ("그릭요거트", "무지방 플레인 그릭요거트 커클랜드 시그니처 907g 2개", ["무지방", "그릭"]),
    "kirkland-ground-cinnamon-303g": ("계피가루", "사이공 계피가루 커클랜드 시그니처 303g", ["사이공", "계피"]),
    "kirkland-instant-coffee-454g": ("인스턴트커피", "커피분말 인스턴트커피 커클랜드 시그니처 454g", ["인스턴트", "커피"]),
    "kirkland-kitchen-drawstring-bag-49l-x200": ("쓰레기봉투", "대용량 끈달린 쓰레기봉투 커클랜드 시그니처 49L 200매", ["대용량", "봉투"]),
    "kirkland-maple-syrup-1l": ("메이플시럽", "단풍 메이플시럽 커클랜드 시그니처 1L", ["메이플", "시럽"]),
    "kirkland-microwave-popcorn-41kg": ("전자레인지팝콘", "대용량 전자레인지 팝콘 커클랜드 시그니처 4.1kg", ["전자레인지", "팝콘"]),
    "kirkland-mineral-water-2l-x6-x6": ("생수", "무라벨 대형 생수 커클랜드 시그니처 2L 36병", ["무라벨", "생수"]),
    "kirkland-mineral-water-500ml-x40-x4": ("생수", "무라벨 생수 커클랜드 시그니처 500ml 160병", ["무라벨", "생수"]),
    "kirkland-nitrile-gloves-medium-400ct": ("니트릴장갑", "중형 니트릴장갑 커클랜드 시그니처 400매", ["니트릴", "장갑"]),
    "kirkland-organic-salsa-108kg-x2": ("살사소스", "유기농 살사소스 커클랜드 시그니처 1.08kg 2개", ["유기농", "살사"]),
    "kirkland-paper-towel-160ct-x12": ("종이타월", "대용량 종이타월 커클랜드 시그니처 160매 12롤", ["종이", "타월"]),
    "kirkland-peanut-butter-pretzel-156kg": ("프레첼", "땅콩버터 프레첼 커클랜드 시그니처 1.56kg", ["땅콩", "프레첼"]),
    "kirkland-pecans-908g": ("피칸", "대용량 피칸 커클랜드 시그니처 908g", ["피칸"]),
    "kirkland-pet-pad-100ct": ("배변패드", "대용량 애견 배변패드 커클랜드 100매", ["배변", "패드"]),
    "kirkland-pink-salt-chips-907g": ("감자칩", "핑크솔트 감자칩 커클랜드 시그니처 907g", ["핑크", "감자"]),
    "kirkland-premium-tissue-40m-x30": ("롤화장지", "3겹 롤화장지 커클랜드 시그니처 40m 30롤", ["3겹", "화장지"]),
    "kirkland-roasted-macadamias-680g": ("마카다미아", "구운 마카다미아 커클랜드 시그니처 680g", ["구운", "마카다미아"]),
    "kirkland-roasted-seaweed-17g-x20": ("구운김", "포장 구운김 커클랜드 시그니처 17g 20봉", ["구운", "김"]),
    "kirkland-ruby-red-grapefruit-juice-284l-x2": ("자몽주스", "홍자몽 주스 커클랜드 시그니처 2.84L 2개", ["홍자몽", "주스"]),
    "kirkland-shelled-pistachios-680g": ("피스타치오", "탈각 피스타치오 커클랜드 시그니처 680g", ["탈각", "피스타치오"]),
    "kirkland-siurana-evoo-1l": ("올리브유", "시우라나 엑스트라버진 올리브유 커클랜드 시그니처 1L", ["시우라나", "올리브"]),
    "kirkland-table-napkins-330ct-x4": ("테이블냅킨", "대용량 테이블냅킨 커클랜드 시그니처 330매 4개", ["테이블", "냅킨"]),
    "kirkland-ultra-liquid-detergent-573l": ("세탁세제", "대용량 액체 세탁세제 커클랜드 시그니처 5.73L", ["액체", "세탁"]),
    "kirkland-unsalted-cashews-113kg": ("캐슈넛", "무염 캐슈넛 대용량 커클랜드 시그니처 1.13kg", ["무염", "캐슈"]),
    "kirkland-unsalted-mixed-nut-snack-packs-45g-x21": ("혼합견과", "무염 혼합견과 스낵팩 커클랜드 시그니처 45g 21봉", ["무염", "혼합"]),
    "kirkland-unsalted-mixed-nuts-113kg": ("믹스넛", "무염 대용량 믹스넛 커클랜드 시그니처 1.13kg", ["무염", "믹스"]),
    "kirkland-unsalted-pistachios-136kg": ("피스타치오", "무염 피스타치오 대용량 커클랜드 시그니처 1.36kg", ["무염", "피스타치오"]),
    "kirkland-walnuts-136kg": ("호두", "호두살 대용량 커클랜드 시그니처 1.36kg", ["호두"]),
    "kirkland-wildflower-honey-227kg": ("벌꿀", "대용량 벌꿀 커클랜드 시그니처 2.27kg", ["벌꿀"]),
    "koong-beef-jerky-280g": ("쇠고기육포", "쇠고기 육포 궁 280g", ["쇠고기", "육포"]),
    "martinellis-apple-juice-296ml-x24": ("사과주스", "PET 사과주스 마티넬리 296ml 24개", ["사과", "주스"]),
    "pocari-sweat-340ml-x20": ("이온음료", "이온음료 포카리스웨트 340ml 20개", ["포카리", "음료"]),
    "ragu-tomato-pasta-sauce-127kg-x3": ("파스타소스", "대용량 토마토 파스타소스 라구 1.27kg 3개", ["토마토", "파스타"]),
    "red-seal-propolis-toothpaste-160g-x4": ("프로폴리스치약", "프로폴리스 치약 레드씰 160g 4개", ["프로폴리스", "치약"]),
    "saputo-cheeseheads-string-cheese-136kg": ("스트링치즈", "오리지널 스트링치즈 사푸토 치즈헤드 1.36kg", ["스트링", "치즈"]),
    "sensodyne-multicare-100g-x5": ("시린이치약", "멀티케어 시린이치약 센소다인 100g 5개", ["시린이", "치약"]),
    "snapik-truffle-cracker-116kg": ("크래커", "트러플 하몽 크래커 스내픽 1.16kg", ["트러플", "크래커"]),
    "starbucks-breakfast-blend-113kg": ("원두", "홀빈 브렉퍼스트 블렌드 스타벅스 원두 1.13kg", ["홀빈", "스타벅스"]),
    "starbucks-caffe-verona-113kg": ("원두", "다크로스트 카페 베로나 스타벅스 원두 1.13kg", ["다크", "스타벅스"]),
    "starbucks-nespresso-60caps": ("캡슐커피", "네스프레소 호환 캡슐커피 스타벅스 60개", ["네스프레소", "스타벅스"]),
    "sunkist-nut-variety-set-25g-x60": ("견과류", "3종 견과류 세트 썬키스트 25g 60봉", ["견과", "썬키스트"]),
    "trefin-belgian-coffee-candy-15kg": ("커피캔디", "벨기에 커피캔디 트레핀 1.5kg", ["커피", "트레핀"]),
    "true-blue-propolis-candy-800g": ("프로폴리스사탕", "호주 프로폴리스사탕 트루블루 800g", ["프로폴리스", "트루블루"]),
    "volvik-flyon-3-piece-golf-ball-24": ("골프공", "3피스 3선 볼빅 플라이온 골프공 24개", ["볼빅", "골프"]),
}


def norm(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", value.lower())


def volume_candidates(seed: str) -> list[dict]:
    records = []
    for item in fetch_keywords([seed]):
        pc, mobile = to_count(item.get("monthlyPcQcCnt")), to_count(item.get("monthlyMobileQcCnt"))
        total = pc + mobile
        if MIN_VOLUME <= total <= MAX_VOLUME and item.get("relKeyword"):
            records.append({"keyword": item["relKeyword"], "monthly_pc_query_count": pc,
                            "monthly_mobile_query_count": mobile, "monthly_query_count": total})
    return sorted(records, key=lambda item: (item["monthly_query_count"], item["keyword"]))


def choose(candidates: list[dict], title: str) -> list[dict]:
    # 상품명에 실제로 들어간 표현만 선택한다. 부분 단어가 우연히 겹친 후보
    # (예: '고양이고급사료', '국산니트릴장갑')는 효능·등급·원산지 오기를 막기 위해 제외한다.
    title_value = norm(title)
    selected = []
    for candidate in candidates:
        value = norm(candidate["keyword"])
        if len(value) >= 3 and value in title_value:
            selected.append({**candidate, "reason": "검증된 최종 상품명에 포함된 직접 연관 검색어"})
    return selected[:2]


def prepare(slug: str, seed: str, title: str, terms: list[str], cache: dict[str, list[dict]], apply: bool, reuse_candidates: bool) -> dict:
    product_dir = ROOT / "products" / slug
    listing_path, research_path = product_dir / "output" / "listing.json", product_dir / "output" / "keyword-research.json"
    listing = json.loads(listing_path.read_text(encoding="utf-8"))
    previous = json.loads(research_path.read_text(encoding="utf-8")) if research_path.exists() else {}
    if seed not in cache:
        cache[seed] = previous.get("candidates", []) if reuse_candidates else volume_candidates(seed)
    candidates = cache[seed]
    selected = choose(candidates, title)
    research = {
        "source": "NAVER Search Ad API Keyword Tool",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "hints": [seed],
        "volume_range": {"min": MIN_VOLUME, "max": MAX_VOLUME},
        "candidates": candidates,
        "selected": selected,
        "excluded_reason": "상품의 브랜드·형태·구성과 직접 일치하지 않거나, 제목에 반복을 유발하는 후보는 제외",
        "title": title,
        "title_strategy": "저조회수 직접 연관어의 속성을 앞에 두고, 일반 상품어는 한 번만 뒤에 배치",
    }
    if apply:
        listing["name"] = title
        listing["detailKeywords"] = [item["keyword"] for item in selected]
        listing_path.write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")
        research_path.write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"slug": slug, "title": title, "selected": selected, "candidate_count": len(candidates)}


def main():
    parser = argparse.ArgumentParser(description="등록 상품의 키워드 근거·제목을 준비")
    parser.add_argument("--apply", action="store_true", help="listing.json 및 keyword-research.json에 저장")
    parser.add_argument("--reuse-candidates", action="store_true", help="저장된 API 후보로 제목·선정 근거만 재검증")
    parser.add_argument("--slugs", nargs="*", help="대상 slug만 처리")
    args = parser.parse_args()
    wanted = set(args.slugs or PLANS)
    unknown = wanted - PLANS.keys()
    if unknown:
        parser.error(f"알 수 없는 slug: {', '.join(sorted(unknown))}")
    cache, results = {}, []
    for slug, (seed, title, terms) in PLANS.items():
        if slug not in wanted:
            continue
        results.append(prepare(slug, seed, title, terms, cache, args.apply, args.reuse_candidates))
        time.sleep(0.3)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
