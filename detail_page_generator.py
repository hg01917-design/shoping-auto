# 스마트스토어 상세페이지 6슬롯 자동 생성 파이프라인
# 사용법:
#   py -3 detail_page_generator.py                    # 인터랙티브 모드
#   py -3 detail_page_generator.py --config my.json   # JSON 설정 파일

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from gemini_analyzer import (
    _connect, _get_or_open_page, _upload_images,
    _send_prompt, _wait_for_response, _extract_response,
    GEMINI_URL, OUTPUT_DIR, STABLE_SECS, MAX_WAIT_SECS,
)

# ── 슬롯 정의 ─────────────────────────────────────────────────────────────────
SLOTS = {
    1: {
        "name": "메인 썸네일",
        "role": "강력한 숫자로 시선 후킹",
        "desc": "제품 패키지 전면 강조 + 핵심 숫자(칼로리·가격·무게 등) 우측 하단 배치",
    },
    2: {
        "name": "품질 보증",
        "role": "비포&애프터 비교로 개선점 시각화",
        "desc": "기존 제품 대비 좋아진 점을 Left(이전)/Right(이후) 구도로 비교",
    },
    3: {
        "name": "타겟 페르소나",
        "role": "3가지 고객 공감 상황",
        "desc": "'이런 분들께 추천해요!' 말풍선 + 캐릭터 일러스트 3컷",
    },
    4: {
        "name": "핵심 스펙 3-Point",
        "role": "3가지 스펙을 아이콘으로 직관 정리",
        "desc": "아이콘 + 스펙명 + 수치를 3열 그리드로 배치, 숫자 크기 2× 강조",
    },
    5: {
        "name": "사용 편의성",
        "role": "간편 사용법 시각화",
        "desc": "1~3단계 순서형 일러스트로 사용 편의성 강조",
    },
    6: {
        "name": "옵션 리스트",
        "role": "다양한 옵션/맛/구성 안내",
        "desc": "옵션별 이미지 + 스펙 카드 그리드 (가로 2~3열)",
    },
}


# ── 입력 설정 ─────────────────────────────────────────────────────────────────
@dataclass
class ProductConfig:
    product_name: str
    specs: list[str]          # 핵심 스펙 3가지 (예: ["30kcal", "글루텐 0%", "당류 ZERO"])
    target: str               # 타겟 고객 (예: "다이어터, 당뇨 관리자")
    brand: str = ""
    hook_number: str = ""     # 가장 강조할 숫자 (없으면 specs[0] 자동 사용)
    before_state: str = ""    # Slot2 비포 상태 설명
    after_state: str = ""     # Slot2 애프터 상태 설명
    usage_steps: list[str] = field(default_factory=list)   # Slot5 사용 단계
    options: list[str] = field(default_factory=list)       # Slot6 옵션 목록
    color_main: str = "white and sky blue"
    color_accent: str = "navy and orange"
    ref_images: list[str] = field(default_factory=list)    # 참고 상품 이미지 경로


# ── 슬롯별 이미지 생성 프롬프트 빌더 ─────────────────────────────────────────
def build_image_prompt(slot_num: int, cfg: ProductConfig) -> str:
    hook = cfg.hook_number or (cfg.specs[0] if cfg.specs else "")
    specs_str = ", ".join(cfg.specs)
    brand = f" by {cfg.brand}" if cfg.brand else ""

    style = (
        f"Korean SmartStore product detail page image style, "
        f"clean infographic design, flat illustration with soft gradients, "
        f"main color {cfg.color_main}, accent color {cfg.color_accent}, "
        f"bright clean background, no people faces, no watermark, "
        f"1:1 square format, high quality product photography mixed with illustration"
    )

    if slot_num == 1:
        return (
            f"Generate an image: Korean SmartStore main thumbnail for '{cfg.product_name}'{brand}. "
            f"Product package centered on clean white background. "
            f"Large bold number '{hook}' displayed prominently at bottom-right with accent color highlight. "
            f"Key specs shown as small badge icons: {specs_str}. "
            f"Eye-catching hooking design that makes viewers stop scrolling. {style}."
        )

    elif slot_num == 2:
        before = cfg.before_state or "기존 제품 (이전 버전 또는 경쟁사 제품)"
        after = cfg.after_state or f"개선된 {cfg.product_name}"
        return (
            f"Generate an image: Korean SmartStore quality proof image for '{cfg.product_name}'{brand}. "
            f"Split-screen before/after comparison layout (left side labeled BEFORE, right side labeled AFTER). "
            f"Left: {before} — shown as dull, plain. "
            f"Right: {after} — shown as vibrant, improved, premium. "
            f"Bold headline at top: '업그레이드!' in large magenta/pink text. "
            f"Arrow or divider between the two sides. {style}."
        )

    elif slot_num == 3:
        t = cfg.target or "건강 관리자, 다이어터, 바쁜 직장인"
        personas = [p.strip() for p in t.replace("，", ",").split(",")][:3]
        while len(personas) < 3:
            personas.append("건강을 챙기는 사람")
        return (
            f"Generate an image: Korean SmartStore target persona image for '{cfg.product_name}'{brand}. "
            f"Headline at top: '이런 분들께 추천해요!' in bold Korean. "
            f"Three character illustrations in a row (no faces, silhouette or simple icons): "
            f"1) {personas[0]} with speech bubble showing their concern, "
            f"2) {personas[1] if len(personas)>1 else personas[0]} with speech bubble, "
            f"3) {personas[2] if len(personas)>2 else personas[0]} with speech bubble. "
            f"Warm friendly illustration style, pastel colors, checkmark icons. {style}."
        )

    elif slot_num == 4:
        s = cfg.specs[:3] if len(cfg.specs) >= 3 else (cfg.specs + ["고품질"] * 3)[:3]
        return (
            f"Generate an image: Korean SmartStore 3-point spec summary for '{cfg.product_name}'{brand}. "
            f"Three-column grid layout with large icons at top of each column. "
            f"Column 1: icon for '{s[0]}' + large bold number/text '{s[0]}' + short description. "
            f"Column 2: icon for '{s[1]}' + large bold number/text '{s[1]}' + short description. "
            f"Column 3: icon for '{s[2]}' + large bold number/text '{s[2]}' + short description. "
            f"Numbers/key values displayed 2x larger than description text. "
            f"Clean white background, each column separated by subtle divider. {style}."
        )

    elif slot_num == 5:
        steps = cfg.usage_steps or ["포장 개봉", "간단 조리 (2분)", "완성 & 섭취"]
        steps_str = " → ".join([f"Step {i+1}: {s}" for i, s in enumerate(steps[:3])])
        return (
            f"Generate an image: Korean SmartStore usage convenience image for '{cfg.product_name}'{brand}. "
            f"Numbered step-by-step horizontal flow: {steps_str}. "
            f"Each step shown as a simple flat icon with number badge (1, 2, 3). "
            f"Large headline emphasizing ease: '누구나 간편하게!' or similar in bold Korean. "
            f"Arrows connecting each step. Bright, clear infographic style. {style}."
        )

    elif slot_num == 6:
        opts = cfg.options or [f"{cfg.product_name} 기본", f"{cfg.product_name} 대용량", f"{cfg.product_name} 선물세트"]
        opts_str = ", ".join(opts[:4])
        return (
            f"Generate an image: Korean SmartStore product option lineup for '{cfg.product_name}'{brand}. "
            f"Grid layout (2 or 3 columns) showing product variants: {opts_str}. "
            f"Each option card contains: product image, option name in bold, key spec badge. "
            f"Clean card design with subtle shadow, consistent style across all options. "
            f"Headline at top: '다양한 구성으로 만나보세요' in bold Korean. {style}."
        )

    return f"Generate an image: product detail page image for {cfg.product_name}, slot {slot_num}. {style}."


# ── 생성된 이미지 추출 ────────────────────────────────────────────────────────
def _extract_generated_images(page) -> list[str]:
    """응답에서 Gemini가 생성한 이미지 URL 추출"""
    return page.evaluate(r"""() => {
        // 마지막 모델 응답 메시지에서 img 태그 수집
        const responseSels = [
            'model-response',
            '.model-response-text',
            'message-content',
            '[data-message-id]',
        ];
        let container = null;
        for (const sel of responseSels) {
            const els = document.querySelectorAll(sel);
            if (els.length > 0) { container = els[els.length - 1]; break; }
        }
        const root = container || document;
        const imgs = [...root.querySelectorAll('img')].filter(img => {
            const src = img.src || '';
            // Gemini 생성 이미지는 blob: 또는 https://storage.googleapis.com/ 등
            return (
                src.startsWith('blob:') ||
                src.includes('generativelanguage') ||
                src.includes('storage.googleapis') ||
                src.includes('gemini') && src.startsWith('https') ||
                (src.startsWith('https') && img.naturalWidth > 200 && img.naturalHeight > 200)
            );
        });
        return imgs.map(img => img.src);
    }""")


def _download_image_from_page(page, url: str, save_path: str) -> bool:
    """Playwright session 쿠키를 이용해 이미지 다운로드"""
    try:
        if url.startswith("blob:"):
            # blob URL → JS로 ArrayBuffer 추출
            b64 = page.evaluate(r"""async (blobUrl) => {
                const r = await fetch(blobUrl);
                const buf = await r.arrayBuffer();
                const bytes = new Uint8Array(buf);
                let bin = '';
                bytes.forEach(b => bin += String.fromCharCode(b));
                return btoa(bin);
            }""", url)
            import base64
            data = base64.b64decode(b64)
            with open(save_path, "wb") as f:
                f.write(data)
            return True
        else:
            # 일반 URL → page.request 사용 (쿠키 포함)
            resp = page.request.get(url)
            if resp.ok:
                with open(save_path, "wb") as f:
                    f.write(resp.body())
                return True
    except Exception as e:
        print(f"[다운로드 실패] {url}: {e}")
    return False


# ── 슬롯 1개 실행 ─────────────────────────────────────────────────────────────
def run_slot(page, slot_num: int, cfg: ProductConfig, out_dir: str) -> dict:
    slot = SLOTS[slot_num]
    print(f"\n[Slot {slot_num}] {slot['name']} — {slot['role']}")

    # 새 대화로 이동 (이전 컨텍스트 초기화)
    page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)

    # 참고 이미지 업로드 (있을 경우)
    uploaded = False
    if cfg.ref_images:
        uploaded = _upload_images(page, cfg.ref_images)
        if uploaded:
            print(f"  참고 이미지 {len(cfg.ref_images)}장 업로드 완료")

    # 이미지 생성 프롬프트 전송
    prompt = build_image_prompt(slot_num, cfg)
    print(f"  프롬프트: {prompt[:120]}...")
    _send_prompt(page, prompt)
    page.wait_for_timeout(3000)

    # 응답 대기
    print(f"  Gemini 응답 대기...")
    _wait_for_response(page)
    page.wait_for_timeout(3000)  # 이미지 렌더링 여유

    # 텍스트 응답 추출
    text_response = _extract_response(page)

    # 생성된 이미지 추출 + 다운로드
    img_urls = _extract_generated_images(page)
    saved_paths = []
    for i, url in enumerate(img_urls):
        ext = ".jpg" if "jpg" in url or "jpeg" in url else ".png"
        fname = f"slot{slot_num:02d}_{slot['name'].replace(' ', '_')}_img{i+1}{ext}"
        save_path = os.path.join(out_dir, fname)
        if _download_image_from_page(page, url, save_path):
            saved_paths.append(save_path)
            print(f"  이미지 저장: {fname}")

    # 이미지가 없으면 스크린샷으로 응답 캡처
    if not saved_paths:
        ss_path = os.path.join(out_dir, f"slot{slot_num:02d}_{slot['name'].replace(' ', '_')}_screenshot.png")
        page.screenshot(path=ss_path, full_page=False)
        saved_paths.append(ss_path)
        print(f"  스크린샷 저장: {os.path.basename(ss_path)}")

    return {
        "slot": slot_num,
        "name": slot["name"],
        "role": slot["role"],
        "prompt": prompt,
        "text_response": text_response,
        "images": saved_paths,
        "ref_images_uploaded": uploaded,
    }


# ── 전체 파이프라인 ────────────────────────────────────────────────────────────
def generate_detail_page(cfg: ProductConfig, slots: list[int] = None) -> dict:
    if slots is None:
        slots = list(range(1, 7))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[^\w가-힣]', '_', cfg.product_name)[:30]
    out_dir = os.path.join(OUTPUT_DIR, f"detail_{safe_name}_{ts}")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    print(f"[+] 출력 디렉토리: {out_dir}")

    results = []
    pw, browser = _connect()
    try:
        page = _get_or_open_page(browser)
        print(f"[Gemini] 연결: {page.url}")

        for slot_num in slots:
            result = run_slot(page, slot_num, cfg, out_dir)
            results.append(result)
            # 슬롯 간 대기 (rate limit 방지)
            if slot_num < max(slots):
                print(f"  다음 슬롯까지 5초 대기...")
                time.sleep(5)

    finally:
        pw.stop()

    # 결과 요약 저장
    summary = {
        "generated_at": datetime.now().isoformat(),
        "product": {
            "name": cfg.product_name,
            "brand": cfg.brand,
            "specs": cfg.specs,
            "target": cfg.target,
        },
        "output_dir": out_dir,
        "slots": results,
    }
    summary_path = os.path.join(out_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n[+] 완료! 요약 저장: {summary_path}")

    # 콘솔 리포트
    print("\n=== 생성 결과 ===")
    for r in results:
        status = f"{len(r['images'])}개 이미지" if r["images"] else "실패"
        print(f"  Slot {r['slot']} [{r['name']}]: {status}")

    return summary


# ── 인터랙티브 입력 ────────────────────────────────────────────────────────────
def _ask(prompt: str, default: str = "") -> str:
    if default:
        val = input(f"{prompt} [{default}]: ").strip()
        return val or default
    return input(f"{prompt}: ").strip()


def interactive_mode() -> ProductConfig:
    print("\n=== 상세페이지 자동 생성 ===\n")
    name = _ask("상품명")
    brand = _ask("브랜드명 (없으면 Enter)")
    hook = _ask("메인 숫자 (예: 30kcal, 없으면 Enter)")

    print("\n핵심 스펙 3가지 입력:")
    specs = []
    for i in range(1, 4):
        s = _ask(f"  스펙 {i}")
        if s:
            specs.append(s)

    target = _ask("\n타겟 고객 (쉼표 구분, 예: 다이어터, 당뇨 관리자)")

    print("\n[Slot 2] 비포&애프터:")
    before = _ask("  이전 상태 설명 (없으면 Enter)")
    after = _ask("  개선 상태 설명 (없으면 Enter)")

    print("\n[Slot 5] 사용 단계 (없으면 Enter로 건너뜀):")
    steps = []
    for i in range(1, 4):
        s = _ask(f"  Step {i}")
        if s:
            steps.append(s)
        else:
            break

    print("\n[Slot 6] 옵션 목록 (없으면 Enter로 건너뜀):")
    options = []
    for i in range(1, 5):
        s = _ask(f"  옵션 {i}")
        if s:
            options.append(s)
        else:
            break

    print("\n참고 이미지 경로 (없으면 Enter로 건너뜀):")
    ref_images = []
    for i in range(1, 4):
        s = _ask(f"  이미지 {i}")
        if s and os.path.exists(s):
            ref_images.append(s)
        elif s:
            print(f"  파일 없음: {s}")
        else:
            break

    color_main = _ask("\n메인 컬러 (영문)", "white and sky blue")
    color_accent = _ask("포인트 컬러 (영문)", "navy and orange")

    return ProductConfig(
        product_name=name,
        brand=brand,
        hook_number=hook,
        specs=specs,
        target=target,
        before_state=before,
        after_state=after,
        usage_steps=steps,
        options=options,
        ref_images=ref_images,
        color_main=color_main,
        color_accent=color_accent,
    )


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="스마트스토어 상세페이지 6슬롯 자동 생성")
    parser.add_argument("--config", help="JSON 설정 파일 경로")
    parser.add_argument("--slots", nargs="+", type=int, default=None,
                        help="생성할 슬롯 번호 (예: --slots 1 2 3)")
    parser.add_argument("--prompts-only", action="store_true",
                        help="프롬프트만 출력하고 Gemini 실행 안 함")
    args = parser.parse_args()

    # 설정 로드
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            data = json.load(f)
        cfg = ProductConfig(**data)
    else:
        cfg = interactive_mode()

    # 프롬프트 미리보기 모드
    if args.prompts_only:
        print("\n=== 슬롯별 생성 프롬프트 ===")
        for i in range(1, 7):
            print(f"\n[Slot {i}] {SLOTS[i]['name']}")
            print(build_image_prompt(i, cfg))
        return

    target_slots = args.slots or list(range(1, 7))
    generate_detail_page(cfg, slots=target_slots)


if __name__ == "__main__":
    main()
