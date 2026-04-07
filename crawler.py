"""
Naver SmartStore 상세페이지 크롤러
- Naver Whale CDP 모드로 연결 (기존 세션 재사용)
- 상세페이지 이미지 URL + 텍스트 추출
- 결과 JSON 저장

Whale 실행 (Windows):
  "C:\Program Files\Naver\Naver Whale\whale.exe" \
    --remote-debugging-port=9223 \
    --user-data-dir="C:\whale-debug"
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import CDP_URL, OUTPUT_DIR, SCROLL_PAUSE_SEC


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def extract_product_id(url: str) -> str:
    match = re.search(r"/products/(\d+)", url)
    return match.group(1) if match else "unknown"


def scroll_to_bottom(page, pause: float = SCROLL_PAUSE_SEC):
    """lazy-load 이미지 로드를 위한 스크롤"""
    prev_height = 0
    while True:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(pause)
        curr_height = page.evaluate("document.body.scrollHeight")
        if curr_height == prev_height:
            break
        prev_height = curr_height
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)


def click_detail_tab(page):
    """상세정보 탭 클릭 시도"""
    candidates = page.query_selector_all("ul[class*=tab] li a, [role=tab], [class*=Tab] a")
    for el in candidates:
        try:
            txt = el.inner_text().strip()
            if txt in ("상세정보", "상품상세", "상세", "Detail"):
                el.click()
                time.sleep(1.5)
                return True
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# 이미지 추출
# ---------------------------------------------------------------------------

def extract_detail_images(page) -> list[str]:
    """상세페이지 이미지 URL 추출"""
    # 1) JavaScript로 전체 img 수집 + 상세 섹션 필터
    result = page.evaluate("""
        () => {
            const detailRoots = [
                '#INTRODUCE',
                '[id*="introduce"]',
                '[id*="detail"]',
                '[class*="Introduce"]',
                '[class*="introduce"]',
                '[class*="detail_content"]',
                '[class*="ProductDescription"]',
            ];

            let container = null;
            for (const sel of detailRoots) {
                container = document.querySelector(sel);
                if (container) break;
            }

            const imgs = container
                ? Array.from(container.querySelectorAll('img'))
                : Array.from(document.querySelectorAll('img'));

            return imgs
                .map(img => img.src || img.dataset.src || img.dataset.lazySrc || '')
                .filter(src => src.startsWith('http'));
        }
    """)

    # 2) iframe 내부 탐색 (SmartEditor 2 기반 상세페이지)
    seen = set(result)
    imgs = list(result)

    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            frame_imgs = frame.evaluate("""
                () => Array.from(document.querySelectorAll('img'))
                    .map(img => img.src || img.dataset.src || '')
                    .filter(src => src.startsWith('http'))
            """)
            for src in frame_imgs:
                if src not in seen:
                    seen.add(src)
                    imgs.append(src)
        except Exception:
            pass

    # 3) pstatic / shop-phinf CDN 이미지만 별도 필터링 (상세 이미지 특징)
    detail_imgs = [
        s for s in imgs
        if any(cdn in s for cdn in ["shop-phinf.pstatic.net", "se2-images", "smartstore"])
    ]

    # 상세 이미지를 못 찾으면 전체 반환
    return detail_imgs if detail_imgs else imgs


# ---------------------------------------------------------------------------
# 텍스트 추출
# ---------------------------------------------------------------------------

def extract_texts(page) -> dict:
    """상품 주요 텍스트 추출"""
    result = page.evaluate("""
        () => {
            function firstText(selectors) {
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const t = el.innerText.trim();
                        if (t) return t;
                    }
                }
                return '';
            }

            function allTexts(selectors) {
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    const texts = Array.from(els)
                        .map(el => el.innerText.trim())
                        .filter(t => t.length > 1);
                    if (texts.length) return texts;
                }
                return [];
            }

            // 상세 섹션 전체 텍스트
            const detailRoots = ['#INTRODUCE', '[class*="Introduce"]', '[class*="introduce"]', '[class*="detail_content"]'];
            let detailText = '';
            for (const sel of detailRoots) {
                const el = document.querySelector(sel);
                if (el) { detailText = el.innerText.trim(); break; }
            }

            return {
                product_name: firstText([
                    'h3._22kNQuEXmb', 'h3.product_title', '.product_title',
                    '[class*=productName]', '[class*=product-name]',
                    'h3[class*=title]', 'h2[class*=title]', 'h3', 'h1'
                ]),
                price: firstText([
                    '._1LY7DqCnwR', '[class*=price] em', '[class*=price] strong',
                    '[class*=Price] em', '.price', '[class*=salePrice]'
                ]),
                seller_name: firstText([
                    'a._3vf6QTLVT3', '[class*=sellerName]', '[class*=seller_name]',
                    '[class*=storeName]', '.store_name'
                ]),
                review_count: firstText([
                    '[class*=reviewCount]', '[class*=review_count]', '.review_count'
                ]),
                detail_full_text: detailText,
                description_texts: allTexts([
                    '.se-module-text p', '[class*=description] p',
                    '[class*=Description] p', '#INTRODUCE p'
                ]),
            };
        }
    """)
    return result


# ---------------------------------------------------------------------------
# 메인 크롤러
# ---------------------------------------------------------------------------

def crawl(url: str) -> dict:
    product_id = extract_product_id(url)
    print(f"[*] 크롤링 시작: {url}")
    print(f"[*] 상품 ID: {product_id}")
    print(f"[*] CDP 연결: {CDP_URL}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"[!] CDP 연결 실패: {e}")
            print(f"[!] Whale을 다음 명령으로 먼저 실행해주세요:")
            print(f'    "C:\\Program Files\\Naver\\Naver Whale\\whale.exe" '
                  f'--remote-debugging-port=9223 --user-data-dir="C:\\whale-debug"')
            sys.exit(1)

        # 기존 컨텍스트/페이지 재사용 또는 새 페이지 생성
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        print("[*] 페이지 이동 중...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            print("[!] 페이지 로드 타임아웃 (계속 진행)")

        # 페이지 렌더링 대기
        time.sleep(3)

        # CAPTCHA 감지
        html = page.content()
        if "captcha" in html.lower():
            print("[!] CAPTCHA 감지. 브라우저에서 직접 해결 후 Enter를 누르세요...")
            input()
            time.sleep(2)

        print("[*] 상세정보 탭 클릭 시도...")
        click_detail_tab(page)

        print("[*] 스크롤 중 (lazy-load 이미지 로드)...")
        scroll_to_bottom(page)
        time.sleep(2)

        print("[*] 이미지 URL 추출 중...")
        images = extract_detail_images(page)

        print("[*] 텍스트 추출 중...")
        texts = extract_texts(page)

        page_title = page.title()
        page_url = page.url

        # CDP 모드에서는 브라우저를 닫지 않음 (기존 세션 유지)
        browser.close()

    result = {
        "crawled_at": datetime.now().isoformat(),
        "product_id": product_id,
        "url": page_url,
        "page_title": page_title,
        "texts": texts,
        "detail_images": images,
        "detail_image_count": len(images),
    }

    print(f"[+] 이미지 {len(images)}개 추출 완료")
    print(f"[+] 상품명: {texts.get('product_name', 'N/A')}")
    print(f"[+] 가격: {texts.get('price', 'N/A')}")

    return result


def save_result(result: dict, output_dir: str = OUTPUT_DIR) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    product_id = result.get("product_id", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"product_{product_id}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[+] 결과 저장: {filepath}")
    return filepath


def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://smartstore.naver.com/luty/products/9983116482"

    result = crawl(url)
    filepath = save_result(result)

    print("\n=== 결과 요약 ===")
    print(f"상품명  : {result['texts'].get('product_name', 'N/A')}")
    print(f"가격    : {result['texts'].get('price', 'N/A')}")
    print(f"이미지  : {result['detail_image_count']}개")
    print(f"저장    : {filepath}")


if __name__ == "__main__":
    main()
