import sys; sys.path.insert(0,'.')
from store_menu_build import *
D="/Users/haengboghanna/Desktop/코스트코스마트스토어클로드/헬스펫_블로그형_상세페이지/배너/"
S='/private/tmp/claude-501/-Users-haengboghanna-Desktop--------------/0090a881-ac53-4295-ab45-ad050b34c0c6/scratchpad/'
U="https://smartstore.naver.com/da5so/category/"
def fill_alt(sp, title, body):
    sp.get_by_placeholder("제목을 입력하세요.").nth(-2).fill(title)
    sp.get_by_placeholder("내용을 입력하세요.").last.fill(body)
def upload(sp,m,pc):
    sp.get_by_role("button",name="등록",exact=True).first.click(); sp.wait_for_timeout(2000)
    sp.locator("#FileUploadAndDrag").set_input_files(D+m); sp.wait_for_timeout(3000)
    sp.get_by_text("PC 편집",exact=True).click(); sp.wait_for_timeout(1200)
    sp.locator("#FileUploadAndDrag").set_input_files(D+pc); sp.wait_for_timeout(3000)
    sp.get_by_text("모바일 편집",exact=True).click(); sp.wait_for_timeout(1200)
    sp.locator("#CENTER_MODAL_ROOT_ID").get_by_role("button",name="적용하기").click(); sp.wait_for_timeout(3000)
def link_alt(sp,url):
    sp.locator("label[for='list-link-item-URL']").last.click(); sp.wait_for_timeout(500)
    u=sp.get_by_placeholder("URL을 입력하세요.").last; u.click(); u.type(url,delay=3)
    sp.get_by_text("설정함",exact=True).last.click(); sp.wait_for_timeout(700)
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp(CDP); ctx=b.contexts[0]; sp=admin_page(ctx)
    fill_alt(sp,"국산 반려동물 영양 3종 헬스펫","3개·5개 세트 무료배송 · HACCP 적용 사료공장 제조")
    print('slide1 done',flush=True)
    for (mi,pc,cid,t,body) in [("promo2_m.jpg","promo2_pc.jpg","5aee6dd553004196a927042678c1feba","코스트코관","식품·생활용품 인기 상품 모아보기"),
                               ("promo3_m.jpg","promo3_pc.jpg","00d4debef84641bcb0c7360a9d1fe27c","생활잡화","패션잡화·생활용품·뷰티 한눈에")]:
        sp.get_by_text("이미지 추가",exact=True).last.click(); sp.wait_for_timeout(1500)
        upload(sp,mi,pc); link_alt(sp,U+cid); fill_alt(sp,t,body); print(t,'done',flush=True)
    sp.screenshot(path=S+'promo7.png')
