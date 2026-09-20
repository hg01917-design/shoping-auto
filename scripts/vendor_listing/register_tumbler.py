import glob, html, json, os, sys, time
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import register_new as R
from slicer import load_stack, W
Image.MAX_IMAGE_PIXELS = None
STATE = HERE / "등록결과_텀블러.json"
T = R.ROOT / "텀블러" / "100도 텀블러"
DETAIL = str(T / "따소미상세-원본.jpg"); NOTICE = str(T / "따소미가열텀블러_상품정보고시-.jpg")
MAIN = ["KakaoTalk_20260119_173816318_02.png","KakaoTalk_20260119_173816318_01.png","KakaoTalk_20260119_173816318_03.png","KakaoTalk_20260119_173816318.png"]
CAT = "50002583"
COLOR, BG = "#8A6A4A", "#F7F0E8"
L = {
 "텀블러-단품": dict(n=1, price=144000, ship=3000, name="따소미 무선 가열텀블러 500ml 휴대용 전기포트 온도조절 분유 텀블러",
    tags=["가열텀블러","휴대용전기포트","무선전기포트","분유텀블러","여행용포트","휴대용포트","온도조절포트","전기텀블러","분유포트","보온포트"]),
 "텀블러-2개": dict(n=2, price=288000, ship=0, name="따소미 무선 가열텀블러 500ml 2개 세트 휴대용 전기포트 무료배송",
    tags=["무선전기포트","휴대용전기포트","여행용전기포트","휴대용커피포트","분유포트기","텀블러세트","선물세트","가열텀블러","출수형분유포트","캠핑용전기포트"]),
}
def T_(h,*ps,small=None):
    s='<div class="t"><h2>%s</h2>'%h
    for p in ps: s+='<p>%s</p>'%p
    return s+('<small>%s</small>'%small if small else '')+'</div>'
TEXT = {0: T_("물 끓이는 일, 이제 어디서나","<b>따소미 가열텀블러</b>는 배터리를 넣어 텀블러 안의 물을 직접 데우는 <b>무선 가열 텀블러</b>예요. 37℃부터 100℃까지 온도를 골라 쓸 수 있어요."),
        9: T_("이런 점이 좋아요","<b>500ml 용량</b>, <b>7단계 온도 설정</b>, 터치 패널로 간단하게 조작해요. 겉은 텀블러, 안은 SUS 316 스테인리스라 물을 안심하고 담을 수 있어요."),
        20: T_("사용 전 꼭 확인하세요","가열 중에는 뚜껑을 열지 말고, 뜨거운 물이 들어 있을 때는 조심해서 다뤄 주세요. 사용법과 주의사항은 상세 이미지를 꼭 읽어 주세요.",small="※ 전기용품 안전확인 XU103861-25004, 전파인증 R-R-mo3-TYB-30 (제조·수입 (주)매쉬원)")}
def slices():
    st,_=load_stack([DETAIL]); a=np.asarray(st); H=a.shape[0]
    std=a.reshape(H,-1).astype(np.float32).std(axis=1)
    def blank(y,r=700):
        lo=max(1,y-r); hi=min(H-1,y+r); idx=[i for i in range(lo,hi) if std[i]<5]
        return min(idx,key=lambda i:abs(i-y)) if idx else lo+int(np.argmin(std[lo:hi]))
    cuts=[0]; y=0
    while H-y>2700:
        ny=blank(y+2000)
        if ny<=y+1000: ny=blank(y+2400)
        y=ny; cuts.append(y)
    cuts.append(H)
    ims=[st.crop((0,cuts[i],W,cuts[i+1])) for i in range(len(cuts)-1)]
    n=Image.open(NOTICE).convert("RGB"); ims.append(n.resize((W,int(n.height*W/n.width))))
    return ims
def mains(key):
    out=[]
    for i,f in enumerate(MAIN,1):
        im=Image.open(T/f).convert("RGB"); out.append((f"{key}-{i}.jpg",R.jpeg(im,90)))
    return out
def intro(cfg):
    ship="무료배송" if cfg["ship"]==0 else "배송비 3,000원"; lab="500ml" if cfg["n"]==1 else "500ml × 2개 세트"
    return (f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;"><div style="font-size:22px;font-weight:700;color:{COLOR};">따소미</div>'
            f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0;color:#111;">무선 가열텀블러</div><div style="font-size:30px;font-weight:800;color:#222;">{lab}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:10px;">{cfg["price"]:,}원 · <b style="color:{COLOR}">{ship}</b></div></div>')
def detail(cfg,urls):
    parts=[intro(cfg)]
    for i,u in enumerate(urls):
        parts.append(f'<img src="{u}" alt="따소미 가열텀블러" style="display:block;width:100%;height:auto;margin:0 auto;" />')
        if i in TEXT: parts.append(R.inline(TEXT[i],COLOR,BG))
    parts.append(R.delivery(cfg,COLOR))
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">'+"".join(parts)+"</div>"
def payload(key,cfg,mn,dt):
    fee=({"deliveryFeeType":"UNIT_QUANTITY_PAID","baseFee":cfg["ship"],"deliveryFeePayType":"PREPAID","repeatQuantity":1} if cfg["ship"] else {"deliveryFeeType":"FREE"})
    op={"statusType":"SALE","saleType":"NEW","leafCategoryId":CAT,"name":cfg["name"],"detailContent":dt,
        "images":{"representativeImage":{"url":mn[0]},"optionalImages":[{"url":u} for u in mn[1:9]]},"salePrice":cfg["price"],"stockQuantity":999,
        "deliveryInfo":{"deliveryType":"DELIVERY","deliveryAttributeType":"NORMAL","deliveryCompany":R.STORE.get("delivery_company","CJGLS"),"deliveryBundleGroupUsable":False,"deliveryFee":fee,
                        "claimDeliveryInfo":{"returnDeliveryFee":6000,"exchangeDeliveryFee":6000}},
        "detailAttribute":{"afterServiceInfo":{"afterServiceTelephoneNumber":R.STORE["after_service_telephone"],"afterServiceGuideContent":R.STORE["after_service_guide"]},
          "originAreaInfo":dict(originAreaCode="0200037",importer="(주)매쉬원",content="중국(수입: (주)매쉬원)",plural=False),"minorPurchasable":True,"taxType":"TAX",
          "naverShoppingSearchInfo":{"brandName":"따소미","manufacturerName":"(주)매쉬원","modelName":"TYB-30"},"sellerCommentUsable":False,
          "productInfoProvidedNotice":{"productInfoProvidedNoticeType":"HOME_APPLIANCES","homeAppliances":{
              "itemName":"따소미 무선 가열텀블러","modelName":"TYB-30","certificationType":"전기용품 안전확인 XU103861-25004 / 방송통신기자재 적합등록 R-R-mo3-TYB-30",
              "ratedVoltage":"상세페이지 참조","powerConsumption":"상세페이지 참조","energyEfficiencyRating":"해당없음","releaseDateText":"2026","manufacturer":"(주)매쉬원",
              "size":"500ml","additionalCost":"없음","warrantyPolicy":"관련 법 및 소비자분쟁해결 규정에 따름","afterServiceDirector":"(주)매쉬원 031-763-2941"}},
          "certificationTargetExcludeContent":{"childCertifiedProductExclusionYn":True,"kcCertifiedProductExclusionYn":"TRUE","greenCertifiedProductExclusionYn":True},
          "seoInfo":{"sellerTags":[{"text":t} for t in cfg["tags"]]}}}
    return {"originProduct":op,"smartstoreChannelProduct":{"naverShoppingRegistration":True,"channelProductDisplayStatusType":"ON"}}
def main():
    only=sys.argv[1] if len(sys.argv)>1 else None
    state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}; cache=None
    for key,cfg in L.items():
        if only and only!=key: continue
        if state.get(key,{}).get("productNo"): print("[=]",key); continue
        if cache is None:
            cache=R.upload([(f"tb-{i:02d}.jpg",R.jpeg(im)) for i,im in enumerate(slices())]); print(f"[+] 상세 {len(cache)}조각",flush=True)
        r=R.post_with_retry(payload(key,cfg,R.upload(mains(key)),detail(cfg,cache)))
        if r.status_code!=200:
            print(f"[!] {key} {r.status_code}: {r.text[:900]}",flush=True); state[key]={"error":r.text[:900]}; STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); continue
        d=r.json(); state[key]={"productNo":d.get("smartstoreChannelProductNo") or d.get("productNo"),"originProductNo":d.get("originProductNo"),"price":cfg["price"]}
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); print(f"[+] {key} 등록 {state[key]['productNo']}",flush=True)
if __name__=="__main__": main()
