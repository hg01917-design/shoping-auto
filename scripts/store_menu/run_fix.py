import sys; sys.path.insert(0,'.')
import store_menu_build as m
from store_menu_build import *
from costco_plan import load
d=load()
plan={}
c=d['코스트코관']; c['반려동물용품']=c.pop('반려동물'); plan.update(c); plan.update(d['생활잡화'])
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp(CDP); ctx=b.contexts[0]; sp=admin_page(ctx)
    sp.on("dialog", lambda d:d.accept())
    for x in [x for x in ctx.pages if 'channel-search/popup' in x.url]: x.close()
    for name,ids in plan.items():
        m.select_cat(sp,name); print(name,len(ids),flush=True)
        m.link_products(ctx,sp,ids); print('  ',m.total_count(sp),flush=True)
        m.apply(sp); print('  저장',flush=True)
print('DONE',flush=True)
