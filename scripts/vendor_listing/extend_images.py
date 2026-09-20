import json, sys, time, io, requests
from PIL import Image
sys.path.insert(0,'.'); sys.path.insert(0,'../../shoping-auto/scripts')
import register_new as R
from naver_auth import API_BASE, auth_headers
def square(stack, y, size=780):
    x=(stack.width-size)//2
    return stack.crop((x,y,x+size,y+size)).resize((1000,1000),Image.LANCZOS)
def extend(keys_state, crops, prefix, max_total=10):
    """keys_state: {key: originProductNo}; crops: [PIL 이미지] → 각 상품의 추가 이미지로 붙인다(대표 포함 최대 10장)."""
    files=[(f"{prefix}-x{i}.jpg",R.jpeg(c,90)) for i,c in enumerate(crops,1)]
    urls=R.upload(files); print(prefix,'업로드',len(urls),flush=True)
    for key,o in keys_state.items():
        for _ in range(3):
            j=requests.get(f"{API_BASE}/v2/products/origin-products/{o}",headers=auth_headers(),timeout=30).json()
            if 'originProduct' in j: break
            time.sleep(2)
        op=j['originProduct']; cur=op['images'].get('optionalImages',[])
        room=max_total-1-len(cur); add=[{"url":u} for u in urls[:max(room,0)]]
        op['images']['optionalImages']=cur+add
        op.pop('customerBenefit',None)
        r=requests.put(f"{API_BASE}/v2/products/origin-products/{o}",headers={**auth_headers(),'Content-Type':'application/json'},json=j,timeout=90)
        print(key,'+',len(add),'→',1+len(cur)+len(add),r.status_code,r.text[:120] if r.status_code!=200 else '',flush=True); time.sleep(1)
