import sys,json; sys.path.insert(0,'.')
import store_menu_build as m
from store_menu_build import *
g=json.load(open('../../신규벤더상품/_work/menu_groups2.json'))
allids=[i for v in g.values() for i in v]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp(CDP); ctx=b.contexts[0]; sp=admin_page(ctx)
    sp.on("dialog", lambda d:d.accept())
    for x in [x for x in ctx.pages if 'channel-search/popup' in x.url]: x.close()
    for name,ids in g.items():
        if not ids: continue
        m.select_cat(sp,name); m.link_products(ctx,sp,ids); print(name,m.total_count(sp),flush=True); m.apply(sp)
    m.select_cat(sp,"국산관"); m.link_products(ctx,sp,allids); print('국산관',m.total_count(sp),flush=True); m.apply(sp)
print('DONE',flush=True)
