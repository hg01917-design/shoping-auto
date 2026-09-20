import sys; sys.path.insert(0,'.')
from store_menu_build import *
D="/Users/haengboghanna/Desktop/코스트코스마트스토어클로드/헬스펫_블로그형_상세페이지/배너/"
S='/private/tmp/claude-501/-Users-haengboghanna-Desktop--------------/0090a881-ac53-4295-ab45-ad050b34c0c6/scratchpad/'
U="https://smartstore.naver.com/da5so/category/"
IDS=["19659a0674634d3d8bf808aeb298efa6","5aee6dd553004196a927042678c1feba","00d4debef84641bcb0c7360a9d1fe27c"]
def close_modal(sp):
    if sp.get_by_text("각 컴포넌트는 최대 5개까지",exact=False).count():
        sp.locator("#CENTER_MODAL_ROOT_ID, .modal, [role=dialog]").first if False else None
        sp.keyboard.press("Escape"); sp.wait_for_timeout(800)
        if sp.get_by_text("각 컴포넌트는 최대 5개까지",exact=False).count():
            sp.locator("#CENTER_MODAL_ROOT_ID button").first.click(); sp.wait_for_timeout(800)
def setup(sp,idx):
    import re
    items=sp.locator("div[role=menuitem]").filter(has_text=re.compile("^자유배너$"))
    items.nth(idx).click(); sp.wait_for_timeout(1500)
    sp.get_by_role("button",name="등록",exact=True).first.click(); sp.wait_for_timeout(2000)
    sp.locator("#FileUploadAndDrag").set_input_files(D+f"free{idx+1}_m.jpg"); sp.wait_for_timeout(3000)
    sp.get_by_text("PC 편집",exact=True).click(); sp.wait_for_timeout(1200)
    sp.locator("#FileUploadAndDrag").set_input_files(D+f"free{idx+1}_pc.jpg"); sp.wait_for_timeout(3000)
    sp.get_by_text("모바일 편집",exact=True).click(); sp.wait_for_timeout(1200)
    sp.locator("#CENTER_MODAL_ROOT_ID").get_by_role("button",name="적용하기").click(); sp.wait_for_timeout(3000)
    sp.get_by_text("URL",exact=True).first.click(); sp.wait_for_timeout(600)
    u=sp.get_by_placeholder("URL을 입력하세요.").first; u.click(); u.type(U+IDS[idx],delay=3)
    print(idx+1,'완료',flush=True)
if __name__=='__main__':
    with sync_playwright() as p:
        b=p.chromium.connect_over_cdp(CDP); ctx=b.contexts[0]; sp=admin_page(ctx)
        close_modal(sp)
        setup(sp,0)
        sp.screenshot(path=S+'free_a.png')
