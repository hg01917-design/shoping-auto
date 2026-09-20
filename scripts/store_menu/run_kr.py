import sys,json; sys.path.insert(0,'.')
import store_menu_build as m
from store_menu_build import *
g=json.load(open('../../신규벤더상품/_work/menu_groups.json'))
allids=[i for v in g.values() for i in v]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp(CDP); ctx=b.contexts[0]; sp=admin_page(ctx)
    sp.on("dialog", lambda d:d.accept())
    for x in [x for x in ctx.pages if 'channel-search/popup' in x.url]: x.close()
    for name,ids in g.items():
        m.select_cat(sp,name); print(name,len(ids),flush=True)
        m.link_products(ctx,sp,ids); print('  ',m.total_count(sp),flush=True)
        m.apply(sp); print('  저장',flush=True)
    m.select_cat(sp,"국산관"); print('국산관 대분류에 신규',len(allids),flush=True)
    m.link_products(ctx,sp,allids); print('  ',m.total_count(sp),flush=True)
    m.apply(sp)
print('DONE',flush=True)
