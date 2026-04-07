# 스마트스토어 상세페이지 이미지 분석 + 재생성 — Gemini Web UI CDP (port 9222)
# blog-automation-v2/gemini_playwright.py 패턴 재활용

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── 설정 ──────────────────────────────────────────────────────────────────────
CDP_URL_GEMINI   = "http://localhost:9223"
GEMINI_URL       = "https://gemini.google.com/app"
OUTPUT_DIR       = "output"

STABLE_SECS      = 10     # N초 동안 텍스트 변화 없으면 완료
MAX_WAIT_SECS    = 300    # 최대 대기 5분

# 입력창 셀렉터 (blog-automation-v2와 동일)
INPUT_SELS = [
    'div.ql-editor[contenteditable="true"]',
    'rich-textarea .ql-editor',
    'div[role="textbox"][contenteditable="true"]',
    'textarea',
]

# 전송 버튼
SEND_BTN = ', '.join([
    'button[aria-label="Send message"]',
    'button[aria-label="메시지 보내기"]',
    'button[aria-label="Submit"]',
    'button.send-button',
])

# 응답 셀렉터
RESPONSE_SELS = [
    '.model-response-text',
    'message-content .markdown',
    'model-response .markdown-main-panel',
    'div.markdown.markdown-main-panel',
    'div.markdown',
]

# 이미지 업로드 버튼 셀렉터
UPLOAD_BTN_SELS = [
    'button[aria-label*="이미지"]',
    'button[aria-label*="파일"]',
    'button[aria-label*="image"]',
    'button[aria-label*="Upload"]',
    'button[aria-label*="Attach"]',
    'button[data-test-id*="upload"]',
    '[class*="upload"] button',
    'button[jsname="g40H3d"]',   # Gemini 이미지 추가 버튼
]


# ── CDP 연결 ──────────────────────────────────────────────────────────────────
def _connect(cdp_url=CDP_URL_GEMINI):
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(cdp_url)
    except Exception as e:
        pw.stop()
        raise RuntimeError(
            f"CDP 연결 실패: {e}\n"
            f"Gemini가 열린 Chrome을 --remote-debugging-port=9222 로 실행해주세요."
        )
    return pw, browser


def _get_or_open_page(browser, url_contains="gemini.google.com"):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if url_contains in pg.url:
                return pg
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    pg = ctx.new_page()
    pg.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=30000)
    pg.wait_for_timeout(3000)
    return pg


# ── 이미지 업로드 ─────────────────────────────────────────────────────────────
def _upload_images(page, image_paths: list[str]) -> bool:
    """Gemini 웹 UI에 이미지 파일들을 업로드한다.
    흐름: + 버튼(파일 업로드 메뉴) → 파일 업로드 메뉴 항목 → expect_file_chooser"""
    print(f"[Gemini] 이미지 {len(image_paths)}개 업로드 시도...")

    abs_paths = [os.path.abspath(p) for p in image_paths]

    # Gemini는 한 번에 최대 10장까지 업로드 가능 — 초과 시 배치 처리
    BATCH = 10
    batches = [abs_paths[i:i+BATCH] for i in range(0, len(abs_paths), BATCH)]

    for batch_idx, batch in enumerate(batches):
        uploaded = False
        # ── 방법 1: + 버튼 메뉴 → 파일 업로드 → file_chooser ────────────────
        for attempt in range(2):
            try:
                # 메뉴가 닫혀 있으면 열기
                menu_item = page.locator('[data-test-id="local-images-files-uploader-button"]')
                if not menu_item.is_visible(timeout=800):
                    # + 버튼 클릭 (JS 경유 — 인코딩 우회, "열기" 상태만 클릭)
                    page.evaluate(r"""() => {
                        const btns = document.querySelectorAll('button');
                        for (const b of btns) {
                            const la = b.getAttribute('aria-label') || '';
                            if (la.includes('\uba54\ub274') && la.includes('\uc5f4\uae30')) {
                                b.click(); return;
                            }
                        }
                    }""")
                    page.wait_for_timeout(600)

                if not menu_item.is_visible(timeout=2000):
                    raise RuntimeError("메뉴 항목이 보이지 않음")

                with page.expect_file_chooser(timeout=10000) as fc_info:
                    menu_item.click(timeout=5000)
                fc_info.value.set_files(batch)
                page.wait_for_timeout(3000 + len(batch) * 500)
                print(f"[Gemini] 배치 {batch_idx+1}/{len(batches)} 업로드 완료 ({len(batch)}장)")
                uploaded = True
                break
            except Exception as e:
                print(f"[Gemini] 배치 {batch_idx+1} 시도 {attempt+1} 실패: {e}")
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                except Exception:
                    pass

        if not uploaded:
            print(f"[Gemini] 배치 {batch_idx+1} 업로드 실패")
            return False

    return True


# ── 응답 대기 / 추출 (blog-automation-v2 패턴 그대로) ────────────────────────
def _get_response_len(page):
    try:
        return page.evaluate("""() => {
            const sels = [
                '.model-response-text',
                'message-content .markdown',
                'model-response .markdown-main-panel',
                'div.markdown',
                '[class*="response"] p',
            ];
            let longest = '';
            for (const sel of sels) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    const t = els[els.length - 1].innerText || '';
                    if (t.length > longest.length) longest = t;
                }
            }
            return longest.length;
        }""")
    except Exception:
        return 0


def _is_generating(page):
    try:
        stop_sel = ', '.join([
            'button[aria-label="Stop response"]',
            'button[aria-label="응답 중지"]',
            'button[aria-label="Stop generating"]',
            '.stop-button',
        ])
        return page.locator(stop_sel).count() > 0
    except Exception:
        return False


def _wait_for_response(page):
    prev_len, stable = 0, 0
    for _ in range(20):          # 생성 시작 대기 최대 20초
        page.wait_for_timeout(1000)
        if _get_response_len(page) > 50 or _is_generating(page):
            break

    for i in range(MAX_WAIT_SECS):
        page.wait_for_timeout(1000)
        cur = _get_response_len(page)
        if i % 10 == 0 and i > 0:
            print(f"[Gemini] {i}초 경과... ({cur}자, 안정 {stable}초)")

        stable = stable + 1 if cur == prev_len and cur > 0 else 0
        prev_len = cur

        if cur >= 200 and stable >= STABLE_SECS:
            print(f"[Gemini] 응답 완료 ({cur}자)")
            return cur
        if i >= 15 and not _is_generating(page) and stable >= 5 and cur >= 200:
            print(f"[Gemini] 응답 완료 (생성 종료 확인, {cur}자)")
            return cur

    print(f"[Gemini] 대기 시간 초과 ({prev_len}자)")
    return prev_len


_JS_TO_MD = r"""(sel) => {
    function toMd(el) {
        let r = '';
        for (const n of el.childNodes) {
            if (n.nodeType === 3) { r += n.textContent; }
            else if (n.nodeType === 1) {
                const t = n.tagName.toLowerCase();
                if      (t==='strong'||t==='b') r += '**'+toMd(n)+'**';
                else if (t==='em'||t==='i')     r += '*'+toMd(n)+'*';
                else if (t==='h1') r += '\n# '+toMd(n)+'\n';
                else if (t==='h2') r += '\n## '+toMd(n)+'\n';
                else if (t==='h3') r += '\n### '+toMd(n)+'\n';
                else if (t==='p')  r += toMd(n)+'\n\n';
                else if (t==='br') r += '\n';
                else if (t==='li') r += '- '+toMd(n)+'\n';
                else if (t==='ul'||t==='ol') r += '\n'+toMd(n);
                else r += toMd(n);
            }
        }
        return r;
    }
    const els = document.querySelectorAll(sel);
    if (!els.length) return '';
    return toMd(els[els.length-1]).trim();
}"""


def _extract_response(page):
    page.wait_for_timeout(2000)
    for sel in RESPONSE_SELS:
        try:
            text = page.evaluate(_JS_TO_MD, sel)
            if text and len(text) > 50:
                return text
        except Exception:
            pass
    # fallback
    try:
        return page.evaluate("""() => {
            const sels = ['.model-response-text','message-content','[class*="model-response"]'];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                if (els.length > 0) {
                    const t = els[els.length-1].innerText;
                    if (t && t.length > 50) return t;
                }
            }
            return '';
        }""")
    except Exception:
        return "[추출 실패]"


# ── 프롬프트 입력 + 전송 ──────────────────────────────────────────────────────
def _send_prompt(page, prompt: str) -> bool:
    # 입력창 찾기
    input_el = None
    for sel in INPUT_SELS:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                el.wait_for(state="visible", timeout=5000)
                input_el = el
                break
        except Exception:
            pass

    if not input_el:
        print("[Gemini] 입력창을 찾지 못했습니다.")
        return False

    input_el.click()
    page.wait_for_timeout(500)

    # JS로 텍스트 삽입 (blog-automation-v2 패턴)
    page.evaluate("""(text) => {
        const quill = document.querySelector('.ql-editor');
        if (quill) {
            quill.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, text);
            return;
        }
        const tb = document.querySelector('div[role="textbox"][contenteditable="true"]');
        if (tb) {
            tb.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, text);
            return;
        }
        const ta = document.querySelector('textarea');
        if (ta) {
            ta.focus(); ta.value = text;
            ta.dispatchEvent(new Event('input', {bubbles:true}));
        }
    }""", prompt)
    page.wait_for_timeout(800)

    # 전송
    try:
        btn = page.locator(SEND_BTN).first
        if btn.count() > 0:
            btn.click(timeout=5000)
            print("[Gemini] 전송 버튼 클릭")
            return True
    except Exception:
        pass

    page.keyboard.press("Enter")
    print("[Gemini] Enter 키로 전송")
    return True


# ── 메인 함수 1: 상세페이지 이미지 분석 ──────────────────────────────────────
def analyze_detail_images(image_dir: str = None, product_id: str = None) -> dict:
    # 이미지 경로 수집
    if image_dir is None:
        if product_id:
            image_dir = f"{OUTPUT_DIR}/images_{product_id}"
        else:
            import glob
            dirs = sorted(glob.glob(f"{OUTPUT_DIR}/images_*"))
            if not dirs:
                raise FileNotFoundError("output/images_* 폴더가 없습니다.")
            image_dir = dirs[-1]

    image_paths = sorted(
        str(p) for p in Path(image_dir).iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp")
    )
    if not image_paths:
        raise FileNotFoundError(f"{image_dir}에 이미지가 없습니다.")

    print(f"[*] 분석 대상: {len(image_paths)}장 ({image_dir})")

    ANALYSIS_PROMPT = """이 스마트스토어 상세페이지 이미지들을 분석해줘.

다음 항목별로 구체적으로 설명해줘:

## 1. 레이아웃 패턴
- 이미지 구성 순서 (첫 장 ~ 마지막 장)
- 각 이미지의 역할 (제품 소개 / 핵심 기능 / 비교 / 조리법 / 유의사항 등)
- 전체적인 스토리라인 흐름

## 2. 카피 패턴
- 헤드라인 스타일 (의문형 / 감탄형 / 숫자 강조 / 키워드 반복 등)
- 자주 쓰인 카피 패턴과 예시
- 폰트 강조 방식 (크기 대비, 색상 대비, 굵기)

## 3. 색상 스타일
- 메인 컬러 / 포인트 컬러
- 배경색 패턴
- 텍스트 색상 조합

## 4. 재활용 가능한 구조 템플릿
- 이 상세페이지를 다른 상품에 적용할 때 쓸 수 있는 이미지 구성 순서 (슬롯별 역할 정의)
- 각 슬롯에 들어갈 정보 유형"""

    pw, browser = _connect()
    try:
        page = _get_or_open_page(browser)
        print(f"[Gemini] 페이지: {page.url}")

        # 새 대화 시작
        page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # 이미지 업로드
        uploaded = _upload_images(page, image_paths)

        # 프롬프트 전송
        _send_prompt(page, ANALYSIS_PROMPT)
        page.wait_for_timeout(3000)

        # 응답 대기 + 추출
        print("[Gemini] 응답 대기 중...")
        _wait_for_response(page)
        response = _extract_response(page)
        print(f"[Gemini] 추출 완료: {len(response)}자")

    finally:
        pw.stop()

    # 결과 저장
    result = {
        "analyzed_at":   datetime.now().isoformat(),
        "image_dir":     image_dir,
        "image_count":   len(image_paths),
        "images_uploaded": uploaded,
        "prompt":        ANALYSIS_PROMPT,
        "analysis":      response,
    }

    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"{OUTPUT_DIR}/analysis_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[+] 분석 결과 저장: {out_path}")

    return result


# ── 메인 함수 2: 내 상품 정보로 재생성 ───────────────────────────────────────
def generate_my_detail_page(product_info: dict, analysis_path: str = None) -> dict:
    """분석 결과를 바탕으로 내 상품의 상세페이지 기획안을 생성한다.

    product_info 예시:
    {
        "product_name": "청정원 두부면 100g x 5개",
        "brand": "청정원",
        "price": "12,000원",
        "key_features": ["글루텐 0%", "저칼로리 30kcal", "KETO 인증"],
        "target_customer": "다이어터, 당뇨 관리자",
        "selling_points": "기존 면 대비 칼로리 70% 낮음",
        "usage": "비빔면, 국수, 샐러드",
    }
    """
    # 가장 최신 분석 결과 로드
    if analysis_path is None:
        import glob
        files = sorted(glob.glob(f"{OUTPUT_DIR}/analysis_*.json"))
        if not files:
            raise FileNotFoundError("분석 결과가 없습니다. analyze_detail_images() 먼저 실행하세요.")
        analysis_path = files[-1]

    with open(analysis_path, encoding="utf-8") as f:
        analysis = json.load(f)

    print(f"[*] 분석 결과 로드: {analysis_path}")

    GENERATE_PROMPT = f"""아래는 스마트스토어 상세페이지 이미지 분석 결과야:

---
{analysis['analysis']}
---

위 분석 결과의 레이아웃 패턴, 카피 스타일, 색상 구조를 그대로 활용해서
내 상품의 상세페이지 기획안을 만들어줘.

## 내 상품 정보
- 상품명: {product_info.get('product_name', '')}
- 브랜드: {product_info.get('brand', '')}
- 가격: {product_info.get('price', '')}
- 핵심 특징: {', '.join(product_info.get('key_features', []))}
- 타겟 고객: {product_info.get('target_customer', '')}
- 셀링포인트: {product_info.get('selling_points', '')}
- 활용법: {product_info.get('usage', '')}

## 요청사항
분석된 이미지 슬롯 구조에 맞춰서, 각 이미지 슬롯별로:
1. 이미지 제목/역할
2. 헤드라인 카피 (분석된 카피 패턴 적용)
3. 서브 카피 / 설명
4. 색상 가이드 (분석된 색상 스타일 적용)
5. 구성 요소 (텍스트 위치, 이미지 소재 제안)

를 구체적으로 작성해줘. 실제 제작에 바로 활용할 수 있는 수준으로."""

    pw, browser = _connect()
    try:
        page = _get_or_open_page(browser)

        page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        _send_prompt(page, GENERATE_PROMPT)
        page.wait_for_timeout(3000)

        print("[Gemini] 재생성 응답 대기 중...")
        _wait_for_response(page)
        response = _extract_response(page)
        print(f"[Gemini] 재생성 완료: {len(response)}자")

    finally:
        pw.stop()

    result = {
        "generated_at":  datetime.now().isoformat(),
        "product_info":  product_info,
        "analysis_used": analysis_path,
        "prompt":        GENERATE_PROMPT,
        "detail_page_plan": response,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"{OUTPUT_DIR}/detail_page_plan_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[+] 기획안 저장: {out_path}")

    return result


# ── CLI 실행 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "analyze"

    if mode == "analyze":
        result = analyze_detail_images()
        print("\n=== 분석 결과 (앞 500자) ===")
        print(result["analysis"][:500])

    elif mode == "generate":
        # 예시 상품 정보 — 실제 사용 시 수정
        my_product = {
            "product_name": "여기에 상품명 입력",
            "brand": "브랜드명",
            "price": "가격",
            "key_features": ["특징1", "특징2", "특징3"],
            "target_customer": "타겟 고객",
            "selling_points": "주요 셀링포인트",
            "usage": "사용법/활용법",
        }
        result = generate_my_detail_page(my_product)
        print("\n=== 기획안 (앞 500자) ===")
        print(result["detail_page_plan"][:500])

    else:
        print("사용법: py -3 gemini_analyzer.py [analyze|generate]")
