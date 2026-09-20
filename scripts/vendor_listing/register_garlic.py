import argparse, glob, html, json, os, sys, time
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import register_new as R
from slicer import load_stack, W
Image.MAX_IMAGE_PIXELS = None
STATE = HERE / "등록결과_흑마늘.json"
G = R.ROOT / "흑마늘"

FAM = {
 "왕": dict(dir="마늘의왕", detail="마늘의왕/마늘의왕 상세페이지.jpg", color="#5B4030", bg="#F6EDE3", brand="올케어", model="마늘의 왕 올케어 흑마늘",
        mains=["마늘의왕대표이미지-1.png","마늘의왕대표이미지-2.png","마늘의왕대표이미지-3.png"], label="마늘의 왕", short="마늘의왕"),
 "여왕": dict(dir="마늘의여왕", detail="마늘의여왕/마늘의여왕상세페이지ㅣ.jpg", color="#9A3B48", bg="#FBEFF0", brand="올케어", model="마늘의 여왕 올케어 흑마늘",
        mains=["마늘의여왕대표이미지-1.png","마늘의여왕대표이미지-2.png","마늘의여왕대표이미지-3.png","마늘의여왕대표이미지-4.png","마늘의여왕대표이미지-5.png"], label="마늘의 여왕", short="마늘의여왕"),
}
CAT = "50007007"
def T(h,*ps,small=None):
    s='<div class="t">'+(f"<h2>{h}</h2>" if h else "")
    for p in ps: s+=f"<p>{p}</p>"
    return s+(f"<small>{small}</small>" if small else "")+"</div>"
TEXT = {
 "왕": {0: T("진하게 담은 의성 흑마늘","의성에서 자란 마늘을 숙성해 만든 <b>올케어 흑마늘 70ml × 30포</b>예요. 포 한 개씩 뜯어서 간편하게 챙길 수 있어요."),
       4: T("원료는 이렇게 들어 있어요","<b>흑마늘 추출액 67.5% + 흑마늘 23.5%(모두 국내산 의성)</b>에 사과농축액, 벌꿀, 프로폴리스를 더했어요.",small="※ 프로폴리스, 벌꿀 성분이 있어요. 알레르기가 있으신 분은 원재료를 꼭 확인해 주세요.")},
 "여왕": {0: T("자두, 석류, 칡을 더한 흑마늘","<b>올케어 마늘의 여왕</b>은 의성 흑마늘에 자두·석류·칡 등을 함께 넣어 달콤새콤한 맛을 살린 액상차예요. 70ml 포 30개가 들어 있어요."),
        3: T("먼저 마셔 본 분들 이야기","상세 이미지의 후기처럼 <b>맛이 부담 없어서 꾸준히 챙기기 좋다</b>는 반응이 이어졌어요.",small="※ 후기는 제조사가 제공한 내용이며 개인에 따라 다를 수 있습니다.")},
}
COMMON_CAUTION="프로폴리스·벌꿀이 들어 있어 알레르기 체질은 원재료를 확인 후 섭취하세요. 개봉 후 바로 드시고, 직사광선을 피해 서늘한 곳에 보관하세요. 부정·불량식품 신고는 국번없이 1399"
def slices(f):
    st,_=load_stack([str(G/f)]); a=np.asarray(st); H=a.shape[0]
    std=a.reshape(H,-1).astype(np.float32).std(axis=1)
    def blank(y,r=600):
        lo=max(1,y-r); hi=min(H-1,y+r); idx=[i for i in range(lo,hi) if std[i]<5]
        return min(idx,key=lambda i:abs(i-y)) if idx else lo+int(np.argmin(std[lo:hi]))
    cuts=[0]; y=0
    while H-y>2600:
        ny=blank(y+1900)
        if ny<=y+900: ny=blank(y+2300)
        y=ny; cuts.append(y)
    cuts.append(H); return [st.crop((0,cuts[i],W,cuts[i+1])) for i in range(len(cuts)-1)]
def mains(key,fam):
    out=[]
    for i,f in enumerate(FAM[fam]["mains"][:5],1):
        im=Image.open(G/FAM[fam]["dir"]/f).convert("RGB"); s=max(im.size); c=Image.new("RGB",(s,s),"white"); c.paste(im,((s-im.width)//2,(s-im.height)//2))
        if s<800: c=c.resize((800,800),Image.LANCZOS)
        out.append((f"{key}-{i}.jpg",R.jpeg(c,90)))
    return out
L={}
for fam,label in [("왕","마늘의 왕"),("여왕","마늘의 여왕")]:
    L[f"{fam}-단품"]=dict(fam=fam,n=1,price=48000,ship=3000,name=f"올케어 {label} 흑마늘 진액 30포 의성 흑마늘즙 액상차",
        tags=["흑마늘즙","흑마늘진액","의성흑마늘진액","발효흑마늘","흑마늘액","의성흑마늘즙","흑마늘액기스","올케어","흑마늘30포","액상차"])
    L[f"{fam}-2개"]=dict(fam=fam,n=2,price=94900,ship=0,name=f"{label} 올케어 흑마늘 30포 2개 세트 의성 흑마늘즙 무료배송",
        tags=["흑마늘선물세트","흑마늘즙","흑마늘진액","의성마늘","흑마늘액기스","흑마늘추천","명절선물","부모님선물","흑마늘60포","올케어흑마늘"])
    L[f"{fam}-3개"]=dict(fam=fam,n=3,price=139900,ship=0,name=f"올케어 {label} 흑마늘 진액 30포 3개 세트 의성 흑마늘즙 무료배송",
        tags=["흑마늘엑기스","흑마늘진액","흑마늘즙","흑마늘선물세트","통흑마늘","발효흑마늘","의성흑마늘","흑마늘90포","가족선물","올케어흑마늘"])
def intro(cfg):
    f=FAM[cfg["fam"]]; c=f["color"]; ship="무료배송" if cfg["ship"]==0 else "배송비 3,000원"
    lab="30포" if cfg["n"]==1 else f'30포 × {cfg["n"]}개'
    return (f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;"><div style="font-size:22px;font-weight:700;color:{c};">올케어</div>'
            f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0;color:#111;">{f["label"]} 흑마늘</div>'
            f'<div style="font-size:30px;font-weight:800;color:#222;">{lab} (70ml)</div>'
            f'<div style="font-size:26px;color:#444;margin-top:10px;">{cfg["price"]:,}원 · <b style="color:{c}">{ship}</b></div></div>')
def detail(cfg,urls):
    f=FAM[cfg["fam"]]; parts=[intro(cfg)]
    for i,u in enumerate(urls):
        parts.append(f'<img src="{u}" alt="{f["model"]}" style="display:block;width:100%;height:auto;margin:0 auto;" />')
        if i in TEXT[cfg["fam"]]: parts.append(R.inline(TEXT[cfg["fam"]][i],f["color"],f["bg"]))
    parts.append(R.delivery(cfg,f["color"]))
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">'+"".join(parts)+"</div>"
def payload(key,cfg,mn,dt):
    f=FAM[cfg["fam"]]
    fee=({"deliveryFeeType":"UNIT_QUANTITY_PAID","baseFee":cfg["ship"],"deliveryFeePayType":"PREPAID","repeatQuantity":1} if cfg["ship"] else {"deliveryFeeType":"FREE"})
    wt=f'70ml × 30포 × {cfg["n"]}개' if cfg["n"]>1 else "70ml × 30포"
    ing="흑마늘 추출액 67.5%(국내산 의성), 흑마늘 23.5%(국내산 의성), 사과농축액(국산), 벌꿀, 프로폴리스"+(", 자두·석류·칡 등 (마늘의 여왕)" if cfg["fam"]=="여왕" else "")
    op={"statusType":"SALE","saleType":"NEW","leafCategoryId":CAT,"name":cfg["name"],"detailContent":dt,
        "images":{"representativeImage":{"url":mn[0]},"optionalImages":[{"url":u} for u in mn[1:9]]},"salePrice":cfg["price"],"stockQuantity":999,
        "deliveryInfo":{"deliveryType":"DELIVERY","deliveryAttributeType":"NORMAL","deliveryCompany":R.STORE.get("delivery_company","CJGLS"),"deliveryBundleGroupUsable":False,"deliveryFee":fee,
                        "claimDeliveryInfo":{"returnDeliveryFee":6000,"exchangeDeliveryFee":6000}},
        "detailAttribute":{"afterServiceInfo":{"afterServiceTelephoneNumber":R.STORE["after_service_telephone"],"afterServiceGuideContent":R.STORE["after_service_guide"]},
          "originAreaInfo":dict(originAreaCode="00",content="국산",plural=False),"minorPurchasable":True,"taxType":"TAX",
          "naverShoppingSearchInfo":{"brandName":"올케어","manufacturerName":"웰빙바이오","modelName":f["model"]},"sellerCommentUsable":False,
          "productInfoProvidedNotice":{"productInfoProvidedNoticeType":"GENERAL_FOOD","generalFood":{
              "productName":f["model"],"foodType":"액상차","producer":"웰빙바이오","location":"경북 의성군 비안면 강변길 111",
              "packDateText":"제품 포장에 별도 표시","consumptionDateText":"제품 포장에 별도 표시일까지","weight":wt,"amount":wt,"ingredients":ing,
              "nutritionFacts":"1포(70ml)당 열량 40kcal, 나트륨 4mg, 탄수화물 9g(당류 6g), 지방 0g, 단백질 1g 미만, 콜레스테롤 0mg",
              "geneticallyModified":False,"consumerSafetyCaution":COMMON_CAUTION,"importDeclarationCheck":False,"customerServicePhoneNumber":R.STORE["after_service_telephone"]}},
          "unitCapacity":{"unitPriceYn":True,"totalCapacityValue":70*30*cfg["n"],"unitCapacity":100,"indicationUnit":"ml"},
          "certificationTargetExcludeContent":{"childCertifiedProductExclusionYn":True,"kcCertifiedProductExclusionYn":"TRUE","greenCertifiedProductExclusionYn":True},
          "seoInfo":{"sellerTags":[{"text":t} for t in cfg["tags"]]}}}
    return {"originProduct":op,"smartstoreChannelProduct":{"naverShoppingRegistration":True,"channelProductDisplayStatusType":"ON"}}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dry",action="store_true"); ap.add_argument("--only"); a=ap.parse_args()
    state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}; cache={}
    for key,cfg in L.items():
        if a.only and a.only!=key: continue
        if state.get(key,{}).get("productNo"): print(f"[=] {key}"); continue
        fam=cfg["fam"]
        if a.dry:
            n=len(slices(FAM[fam]["detail"])); print(f"[dry] {key}: 이름 {len(cfg['name'])}자 조각 {n} 태그 {len(cfg['tags'])}"); continue
        if fam not in cache:
            cache[fam]=R.upload([(f"g{fam}-{i:02d}.jpg",R.jpeg(im)) for i,im in enumerate(slices(FAM[fam]["detail"]))]); print(f"[+] {fam} 상세 {len(cache[fam])}조각",flush=True)
        mn=R.upload(mains(key,fam)); r=R.post_with_retry(payload(key,cfg,mn,detail(cfg,cache[fam])))
        if r.status_code!=200:
            print(f"[!] {key} {r.status_code}: {r.text[:800]}",flush=True); state[key]={"error":r.text[:800]}; STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); continue
        d=r.json(); state[key]={"productNo":d.get("smartstoreChannelProductNo") or d.get("productNo"),"originProductNo":d.get("originProductNo"),"name":cfg["name"],"price":cfg["price"]}
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); print(f"[+] {key} 등록 {state[key]['productNo']}",flush=True); time.sleep(1)
if __name__=="__main__": main()
