# Naver SmartStore 상세페이지 크롤러 (Whale CDP 연결)
#
# 사전 조건:
#   Whale을 CDP 모드로 실행 (Windows):
#   "C:\\Program Files\\Naver\\Naver Whale\\whale.exe"
#       --remote-debugging-port=9223 --user-data-dir="C:\\whale-debug"
#
# 사용법:
#   py -3 extract_from_cdp.py [URL]

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import CDP_URL, OUTPUT_DIR, SCROLL_PAUSE_SEC

DEFAULT_URL = "https://smartstore.naver.com/luty/products/9983116482"


# ──────────────────────────────────────────────
# JS 추출 페이로드 (한 번의 evaluate로 처리)
# ──────────────────────────────────────────────
JS_EXTRACT = r"""
() => {
    // ── JSON-LD (가장 신뢰할 수 있는 구조화 데이터) ───────────────────────
    let ldName = '', ldPrice = 0, ldCurrency = 'KRW', ldCategory = '';
    try {
        const ldEl = document.querySelector('script[type="application/ld+json"]');
        if (ldEl) {
            const ld = JSON.parse(ldEl.textContent);
            // " : 스토어명" 접미사 제거
            ldName = (ld.name || '').replace(/\s*:\s*[^:]+$/, '').trim();
            ldPrice = (ld.offers && ld.offers.price) ? ld.offers.price : 0;
            ldCurrency = (ld.offers && ld.offers.priceCurrency) || 'KRW';
            ldCategory = ld.category || '';
        }
    } catch(e) {}

    // ── 할인율 (원래가격 → 할인가) ─────────────────────────────────────
    let originalPrice = 0;
    try {
        const ogPriceEl = document.querySelector('.e1DMQNBPJ_');
        if (ogPriceEl) {
            originalPrice = parseInt((ogPriceEl.innerText || '').replace(/[^0-9]/g, ''), 10) || 0;
        }
    } catch(e) {}

    // ── 판매자: og:description에서 "[스토어명]" 패턴 추출 ────────────────
    let sellerName = '';
    try {
        const ogDesc = document.querySelector('meta[property="og:description"]');
        if (ogDesc) {
            const m = (ogDesc.getAttribute('content') || '').match(/^\[([^\]]+)\]/);
            if (m) sellerName = m[1];
        }
    } catch(e) {}

    // ── 리뷰수 ───────────────────────────────────────────────────────────
    let reviewCount = '';
    try {
        const reviewState = (window.__PRELOADED_STATE__ || {}).productReviewSummary;
        if (reviewState && reviewState.A) {
            const total = reviewState.A.totalCount || reviewState.A.reviewCount;
            if (total !== undefined) reviewCount = String(total);
        }
    } catch(e) {}

    // ── 상세 컨테이너 (#INTRODUCE) ───────────────────────────────────────
    const detailEl = document.querySelector('#INTRODUCE')
        || document.querySelector('[class*=Introduce]')
        || document.querySelector('[class*=introduce]');

    // ── 상세 이미지: data-src 우선 (SE2 lazy-load) ───────────────────────
    //    썸네일(type=f*, m*숫자) 제외
    const THUMB_RE = /[?&]type=(f|m)[0-9]+/;

    function extractImgUrls(root) {
        return [...(root || document).querySelectorAll('img')]
            .map(img => img.dataset.src || img.src || '')
            .filter(src =>
                src.startsWith('http') &&
                !src.startsWith('data:') &&
                !THUMB_RE.test(src)
            );
    }

    const detailImages = detailEl ? extractImgUrls(detailEl) : [];
    const CDN_RE = /shop-phinf\.pstatic\.net/;
    const fallbackImages = detailImages.length
        ? detailImages
        : extractImgUrls(null).filter(s => CDN_RE.test(s));

    const uniqueImages = [...new Set(fallbackImages)];

    // ── 상세 텍스트 ──────────────────────────────────────────────────────
    const detailText = detailEl ? detailEl.innerText.trim() : '';

    return {
        product_name:   ldName,
        price:          ldPrice,
        price_currency: ldCurrency,
        original_price: originalPrice,
        seller_name:    sellerName,
        category:       ldCategory,
        review_count:   reviewCount,
        detail_text:    detailText,
        detail_images:  uniqueImages,
        detail_container_found: !!detailEl,
    };
}
"""


# ──────────────────────────────────────────────
# 스크롤 (lazy-load 활성화)
# ──────────────────────────────────────────────
def scroll_to_bottom(page, pause: float = SCROLL_PAUSE_SEC):
    prev = 0
    while True:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(pause)
        curr = page.evaluate("document.body.scrollHeight")
        if curr == prev:
            break
        prev = curr
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)


# ──────────────────────────────────────────────
# 상세정보 탭 클릭
# ──────────────────────────────────────────────
def click_detail_tab(page) -> bool:
    for el in page.query_selector_all("ul[class*=tab] li a, [role=tab]"):
        try:
            if el.inner_text().strip() in ("상세정보", "상품상세", "상세"):
                el.click()
                time.sleep(1.5)
                return True
        except Exception:
            pass
    return False


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def crawl(url: str) -> dict:
    product_id = (re.search(r"/products/(\d+)", url) or re.Match).group(1) \
        if re.search(r"/products/(\d+)", url) else "unknown"

    with sync_playwright() as p:
        print(f"[*] CDP 연결 중: {CDP_URL}")
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            sys.exit(
                f"[!] CDP 연결 실패: {e}\n"
                f"    Whale을 먼저 실행하세요:\n"
                f'    "C:\\Program Files\\Naver\\Naver Whale\\whale.exe" '
                f'--remote-debugging-port=9223 --user-data-dir="C:\\whale-debug"'
            )

        ctx = browser.contexts[0]

        # 이미 열려 있는 탭 재사용
        page = next((pg for pg in ctx.pages if url in pg.url or pg.url in url), None)
        if page:
            print(f"[*] 기존 탭 재사용: {page.url}")
        else:
            print(f"[*] 새 탭으로 이동: {url}")
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            except PWTimeout:
                print("[!] 로드 타임아웃 (계속 진행)")

        # 로드 완료 대기
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except PWTimeout:
            pass
        time.sleep(3)

        # CAPTCHA 감지 → 사용자에게 알림
        if "captcha" in page.content().lower():
            print("[!] CAPTCHA 감지 — Whale 창에서 직접 풀고 Enter 입력...")
            input()
            time.sleep(2)

        page_title = page.title()
        page_url = page.url
        print(f"[*] 페이지: {page_title}")

        # 상세정보 탭 클릭
        click_detail_tab(page)

        # 스크롤로 lazy-load 이미지 활성화
        print("[*] 스크롤 중...")
        scroll_to_bottom(page)
        time.sleep(2)

        # 데이터 추출
        print("[*] 데이터 추출 중...")
        data = page.evaluate(JS_EXTRACT)

        # CDP 모드: 브라우저 닫지 않음 (세션 유지)
        browser.close()

    return {
        "crawled_at":         datetime.now().isoformat(),
        "product_id":         product_id,
        "url":                page_url,
        "page_title":         page_title,
        "texts": {
            "product_name":   data["product_name"],
            "price":          data["price"],
            "price_currency": data["price_currency"],
            "original_price": data["original_price"],
            "seller_name":    data["seller_name"],
            "category":       data["category"],
            "review_count":   data["review_count"],
            "detail_text":    data["detail_text"],
        },
        "detail_images":      data["detail_images"],
        "detail_image_count": len(data["detail_images"]),
        "_debug": {
            "detail_container_found": data["detail_container_found"],
        },
    }


def save_result(result: dict) -> str:
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(OUTPUT_DIR, f"product_{result['product_id']}_{ts}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return filepath


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    result = crawl(url)
    filepath = save_result(result)

    # 결과 출력 (인코딩 안전하게)
    def safe(s): return s.encode("utf-8", errors="replace").decode("utf-8") if s else ""

    print("\n=== 결과 요약 ===")
    print(f"상품명  : {safe(result['texts']['product_name'])}")
    print(f"가격    : {result['texts']['price']}원 (정가 {result['texts']['original_price']}원)")
    print(f"판매자  : {safe(result['texts']['seller_name'])}")
    print(f"카테고리: {safe(result['texts']['category'])}")
    print(f"이미지  : {result['detail_image_count']}개")
    print(f"저장    : {filepath}")

    print("\n상세 이미지 URL:")
    for img_url in result["detail_images"]:
        print(f"  {img_url}")


if __name__ == "__main__":
    main()
