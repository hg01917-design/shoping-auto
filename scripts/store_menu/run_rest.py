import sys; sys.path.insert(0,'.')
import store_menu_build as m
from store_menu_build import *
from costco_plan import load
d=load()
allc=[i for v in d['코스트코관'].values() for i in v]
misc=d['생활잡화']
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp(CDP); ctx=b.contexts[0]; sp=admin_page(ctx)
    sp.on("dialog", lambda d:d.accept())
    for x in [x for x in ctx.pages if 'channel-search/popup' in x.url]: x.close()
    m.select_cat(sp,"코스트코관"); print('코스트코관 대분류',len(allc),flush=True); m.link_products(ctx,sp,allc); print('  ',m.total_count(sp),flush=True)
    m.apply(sp)
    m.add_children(sp,"생활잡화",list(misc.keys()),"중분류"); m.expand_all(sp)
    print(sp.evaluate("()=>[...document.querySelectorAll('span[data-level]')].map(e=>e.dataset.level+':'+e.textContent.trim())"),flush=True)
    for name,ids in misc.items():
        m.select_cat(sp,name); print(name,len(ids),flush=True); m.link_products(ctx,sp,ids); print('  ',m.total_count(sp),flush=True)
    allm=[i for v in misc.values() for i in v]
    m.select_cat(sp,"생활잡화"); print('생활잡화 대분류',len(allm),flush=True); m.link_products(ctx,sp,allm); print('  ',m.total_count(sp),flush=True)
    m.apply(sp)
print('DONE',flush=True)
