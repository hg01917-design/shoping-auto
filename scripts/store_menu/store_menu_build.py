"""다온나상점 '나만의 카테고리 전시' 구성 도우미 (판매자센터 화면 자동 조작).

디버그 Chrome(9223)에 로그인된 판매자센터의 카테고리&메뉴 관리 화면을 사용한다.
로그인·비밀번호는 다루지 않는다.
"""
import re
import sys
from playwright.sync_api import sync_playwright

CDP = "http://localhost:9223"


def admin_page(ctx):
    return [x for x in ctx.pages if "display-config" in x.url][0]


def expand_all(sp):
    """접힌 하위 카테고리를 모두 펼친다."""
    for _ in range(4):
        btns = sp.locator("button:has(span.blind:text('하위 카테고리 보기'))")
        if btns.count() == 0:
            break
        for i in range(btns.count()):
            try:
                btns.nth(0).click(timeout=2000)
                sp.wait_for_timeout(300)
            except Exception:
                break


def select_cat(sp, name, nth=0):
    """왼쪽 트리에서 카테고리를 선택한다(글자 위에 덮인 버튼을 클릭)."""
    expand_all(sp)
    label = sp.locator("span[data-level]", has_text=re.compile(rf"^{re.escape(name)}$")).nth(nth)
    cid = label.get_attribute("data-id")
    sp.locator(f'button[aria-labelledby="{cid}"]').click(position={"x": 8, "y": 8})
    sp.wait_for_timeout(1500)


def add_children(sp, parent, names, level_word):
    """parent 카테고리 아래에 하위 카테고리를 추가한다. level_word: 중분류/소분류"""
    select_cat(sp, parent)
    sp.get_by_role("button", name="추가", exact=True).click()
    sp.wait_for_timeout(1000)
    ph = f"{level_word}명을 입력하세요."
    for i, n in enumerate(names):
        if i > 0:
            sp.get_by_text("카테고리 추가", exact=True).first.click()
            sp.wait_for_timeout(300)
        sp.get_by_placeholder(ph).nth(i).fill(n)
    sp.get_by_role("button", name="저장").click()
    sp.wait_for_timeout(2500)


def ensure_individual_link(sp):
    r = sp.get_by_text("개별상품 단위로 연결", exact=True)
    if r.count():
        r.click()
        sp.wait_for_timeout(800)


def _open_popup(ctx, sp):
    sp.get_by_role("button", name="상품 추가").click()
    for _ in range(30):
        sp.wait_for_timeout(500)
        cand = [x for x in ctx.pages if "channel-search/popup" in x.url]
        if cand:
            pop = cand[0]
            pop.set_viewport_size({"width": 1400, "height": 12000})
            pop.wait_for_selector(".ag-center-cols-container .ag-row", timeout=20000)
            pop.wait_for_timeout(1500)
            return pop
    raise RuntimeError("상품 찾기 팝업이 열리지 않음")


def _select_on_page(pop, want):
    """현재 페이지를 스크롤하며 want에 있는 행의 체크박스를 실제 마우스로 클릭한다."""
    pop.evaluate("()=>{document.querySelector('.ag-body-viewport').scrollTop=0}")
    pop.wait_for_timeout(400)
    got = set()
    for _ in range(200):
        vis = pop.evaluate(
            """()=>{const vp=document.querySelector('.ag-body-viewport').getBoundingClientRect(); const out=[];
              for(const r of document.querySelectorAll('.ag-center-cols-container .ag-row')){
                const pid=[...r.querySelectorAll('.ag-cell')].map(x=>x.textContent.trim()).find(t=>/^\\d{11}$/.test(t));
                const c=r.querySelector('.ag-selection-checkbox'); if(!pid||!c) continue;
                const b=c.getBoundingClientRect();
                if(b.top+b.height/2>=vp.top+8 && b.top+b.height/2<=vp.bottom-8) out.push([pid,b.left+b.width/2,b.top+b.height/2]);
              } return out}"""
        )
        for pid, x, y in vis:
            if pid in want and pid not in got:
                pop.mouse.click(x, y)
                got.add(pid)
                pop.wait_for_timeout(120)
        moved = pop.evaluate(
            """()=>{const v=document.querySelector('.ag-body-viewport'); const b=v.scrollTop; v.scrollTop=b+110; return v.scrollTop!==b}"""
        )
        pop.wait_for_timeout(250)
        if not moved or got == want:
            break
    return got


def link_products(ctx, sp, ids):
    """선택된 카테고리에 상품번호 목록을 연결한다(페이지마다 팝업을 열어 선택 후 등록)."""
    ensure_individual_link(sp)
    want = set(ids)
    done = set()
    for page_no in range(1, 8):
        pop = _open_popup(ctx, sp)
        if page_no > 1:
            btn = pop.locator("li._page a").filter(has_text=re.compile(rf"^\s*{page_no}\s*$"))
            if btn.count() == 0:
                pop.get_by_role("button", name="취소").click()
                sp.wait_for_timeout(800)
                break
            btn.first.click()
            pop.wait_for_timeout(1800)
        got = _select_on_page(pop, want - done)
        if got:
            pop.get_by_role("button", name="상품등록").click()
            done |= got
            sp.wait_for_timeout(2500)
        else:
            pop.get_by_role("button", name="취소").click()
            sp.wait_for_timeout(800)
        if done == want:
            break
    print("  연결", len(done), "/", len(want), "누락:", sorted(want - done)[:5])
    return len(done), want - done


def apply(sp):
    sp.get_by_role("button", name="적용하기").click()
    sp.wait_for_timeout(2500)


def total_count(sp):
    try:
        return sp.get_by_text("총 상품 수").first.inner_text().replace("\n", " ")
    except Exception:
        return "?"
