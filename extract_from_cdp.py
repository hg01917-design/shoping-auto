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
    // ── 헬퍼 ───────────────────────────────────────────────────────────
    function firstText(sels) {
        for (const s of sels) {
            try {
                const el = document.querySelector(s);
                if (el) { const t = (el.innerText || '').trim(); if (t) return t; }
            } catch(e) {}
        }
        return '';
    }

    // ── 상품명 ──────────────────────────────────────────────────────────
    const productName = firstText([
        'h3._22kNQuEXmb', 'h3.product_title', '.product_title',
        '[class*=productName]', '[class*=product-name]',
        'h3[class*=title]', 'h2[class*=title]', 'h3'
    ]);

    // ── 가격: 텍스트가 "숫자,숫자원" 패턴인 leaf 요소 중 첫 번째 ─────────
    const priceEl = [...document.querySelectorAll('*')]
        .find(el => {
            if (el.children.length > 0) return false;
            const t = (el.innerText || '').trim();
            return /^[0-9,]+원$/.test(t);
        });
    const price = priceEl ? priceEl.innerText.trim() : '';

    // ── 판매자(스토어명) ────────────────────────────────────────────────
    // href가 스토어 경로인 링크에서 스토어명 추출
    function getStoreName() {
        // 방법 1: 스토어 경로 링크에서 텍스트
        const storeLinks = document.querySelectorAll('a[href*="/luty"], a[href*="smartstore.naver.com/"]');
        for (const a of storeLinks) {
            const t = (a.innerText || '').trim();
            if (t && t.length < 30 && !t.includes('\n')) return t;
        }
        // 방법 2: 클래스명 기반
        const byClass = firstText([
            '.store_link', '.store_name', '[class*=storeName]',
            '[class*=StoreInfo] a', '[class*=seller_name]', '[class*=sellerName]',
        ]);
        if (byClass) return byClass;
        return '';
    }
    const sellerName = getStoreName();

    // ── 리뷰수 ──────────────────────────────────────────────────────────
    const reviewCount = firstText([
        '[class*=reviewCount]', '[class*=review_count]',
        '[class*=ReviewCount]',
    ]);

    // ── 상세 컨테이너 (#INTRODUCE) ──────────────────────────────────────
    const detailEl = document.querySelector('#INTRODUCE')
        || document.querySelector('[class*=Introduce]')
        || document.querySelector('[class*=introduce]');

    // ── 상세 이미지: data-src 우선, 없으면 src ──────────────────────────
    //    썸네일(f40, f80, m120 등) 제외 — type=w860, w640, m1000 등만 허용
    const THUMB_RE = /[?&]type=(f|m)[0-9]+/;

    function extractImgUrls(root) {
        return Array.from((root || document).querySelectorAll('img'))
            .map(img => img.dataset.src || img.src || '')
            .filter(src =>
                src.startsWith('http') &&
                !src.startsWith('data:') &&
                !THUMB_RE.test(src)
            );
    }

    const detailImages = detailEl ? extractImgUrls(detailEl) : [];

    // 상세 이미지가 없으면 전체에서 shop-phinf CDN + 대형 이미지만
    const CDN_RE = /shop-phinf\.pstatic\.net/;
    const fallbackImages = detailImages.length
        ? detailImages
        : extractImgUrls(null).filter(s => CDN_RE.test(s));

    // 중복 제거
    const uniqueImages = [...new Set(fallbackImages)];

    // ── 상세 텍스트 ─────────────────────────────────────────────────────
    const detailText = detailEl ? detailEl.innerText.trim() : '';

    return {
        product_name: productName,
        price:        price,
        seller_name:  sellerName,
        review_count: reviewCount,
        detail_text:  detailText,
        detail_images: uniqueImages,
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
            "seller_name":    data["seller_name"],
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
    print(f"가격    : {safe(result['texts']['price'])}")
    print(f"판매자  : {safe(result['texts']['seller_name'])}")
    print(f"이미지  : {result['detail_image_count']}개")
    print(f"저장    : {filepath}")

    print("\n상세 이미지 URL:")
    for img_url in result["detail_images"]:
        print(f"  {img_url}")


if __name__ == "__main__":
    main()
