import re
from playwright.sync_api import sync_playwright

def click_dlg_save(pg):
    pg.on("dialog", lambda d:d.accept())
    pg.locator("button:visible").filter(has_text="저장").last.click(force=True); pg.wait_for_timeout(3500)
    ok=pg.evaluate("()=>document.body.innerText.includes('혜택등록이 완료')")
    return ok

def fill_common(pg, name, target, amount, minorder, months="3개월"):
    pg.on("dialog", lambda d:d.accept())
    pg.goto("https://sell.smartstore.naver.com/#/customer-manage/search",wait_until="domcontentloaded"); pg.wait_for_timeout(2000)
    pg.goto("https://sell.smartstore.naver.com/#/customer-manage/register/",wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    pg.get_by_placeholder("최대 30자 이내로 입력하세요.").fill(name)
    pg.get_by_text(target,exact=True).first.click(); pg.wait_for_timeout(500)
    pg.get_by_text("쿠폰",exact=True).first.click(); pg.wait_for_timeout(1000)
    unit=pg.locator("button.btn.btn-default").filter(has_text="%").first
    unit.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    bb=unit.bounding_box(); unit.click(); pg.wait_for_timeout(500)
    pg.mouse.click(bb["x"]+bb["width"]/2, bb["y"]+bb["height"]+40); pg.wait_for_timeout(500)   # '원'
    pg.mouse.click(bb["x"]-150, bb["y"]+bb["height"]/2); pg.keyboard.type(str(amount)); pg.wait_for_timeout(300)
    mo=pg.locator("input[type=tel]").nth(2); mo.scroll_into_view_if_needed(); mo.click(); pg.keyboard.type(str(minorder)); pg.wait_for_timeout(300)
    pg.get_by_role("button",name=months,exact=True).click(); pg.wait_for_timeout(500)
    return pg.evaluate("()=>[...document.querySelectorAll('input[type=tel]')].map(e=>e.value)")

def pick_products(pg, ids):
    pg.evaluate("()=>{[...document.querySelectorAll('input[name=targetType]')].find(e=>e.value=='PRODUCT').click()}"); pg.wait_for_timeout(1000)
    pg.get_by_role("button",name="상품 불러오기").click(); pg.wait_for_timeout(3500)
    pg.get_by_placeholder(re.compile("복수 검색")).fill(",".join(ids)); pg.get_by_role("button",name="검색",exact=True).click(); pg.wait_for_timeout(3500)
    n=pg.get_by_text("개의 상품이 조회되었습니다").first.inner_text()
    hdr=pg.locator(".ag-header-select-all, th input[type=checkbox]")
    return n

def select_all_and_register(pg):
    hdr=pg.evaluate("""()=>{const t=[...document.querySelectorAll('table thead input[type=checkbox], .table-header input[type=checkbox], th input[type=checkbox]')].filter(e=>e.offsetParent); return t.length}""")
    cbs=pg.locator("input[type=checkbox]")
    cnt=cbs.count()
    for i in range(cnt):
        e=cbs.nth(i)
        if e.is_visible():
            e.scroll_into_view_if_needed(); e.check(force=True); break
    pg.wait_for_timeout(600)
    n=pg.get_by_text("선택된 상품").first.inner_text()
    pg.locator("button:visible").filter(has_text="상품등록").last.click(force=True); pg.wait_for_timeout(2500)
    return n
def confirm_step(pg, name):
    pg.get_by_placeholder("최대 30자 이내로 입력하세요.").fill(name)
    pg.locator("button:visible").filter(has_text="확인").last.click(force=True); pg.wait_for_timeout(2500)
    txt=pg.evaluate("()=>document.body.innerText"); i=txt.find('[전체고객 혜택]')
    return txt[i:i+330].replace('\n',' | ') if i>=0 else txt[:100]
