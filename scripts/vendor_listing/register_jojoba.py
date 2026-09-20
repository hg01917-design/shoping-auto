import glob, html, json, os, re, sys, time
from datetime import datetime
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import register_new as R
Image.MAX_IMAGE_PIXELS = None
STATE = HERE / "등록결과_호호바.json"
D = glob.glob(str(R.ROOT / "순유" / "4.*"))[0]
SLICES = [2,4,5,6,7,8,9,11,12,13,15,16,17]     # 01=벤더 가격표, 03=노화 표현 → 제외
COLOR, BG = "#B8860B", "#FFF8E1"
CAT = "50000443"
L = {
 "호호바-단품": dict(n=1, price=21900, ship=3000, name="순유 호호바오일 50ml 100% 유기농 골든 호호바씨오일 페이스오일 비정제",
    tags=["호호바오일","페이스오일","호호바씨오일","유기농호호바오일","골든호호바오일","호호바오일원액","비정제호호바오일","캐리어오일","식물성오일","페이셜오일"]),
 "호호바-2개": dict(n=2, price=44900, ship=0, name="호호바오일 50ml 2개 세트 페이스오일 순유 100% 호호바씨오일 무료배송",
    tags=["호호바오일추천","호호바오일사용법","호호바오일대용량","천연페이스오일","보습오일","피부오일","얼굴오일","호호바오일2개","오일세럼","에센스오일"]),
 "호호바-3개": dict(n=3, price=66900, ship=0, name="유기농 호호바오일 50ml 3개 세트 비정제 골든호호바 페이셜오일 무료배송",
    tags=["유기농호호바오일","냉압착호호바오일","호호바바디오일","아기호호바오일","호호바오일3개","천연바디오일","마사지오일","베이스오일","호호바","순유"]),
}
def T_(h,*ps,small=None):
    s='<div class="t"><h2>%s</h2>'%h
    for p in ps: s+='<p>%s</p>'%p
    return s+('<small>%s</small>'%small if small else '')+'</div>'
TEXT = {1: T_("성분은 단 하나, 호호바씨오일","<b>100% 호호바씨오일</b> 한 가지로 만든 페이스 오일이에요. 비정제·냉압착 방식의 원액이라 다른 성분 걱정 없이 쓸 수 있어요.",small="※ 전성분: 호호바씨오일 100%"),
        6: T_("이렇게 사용해 보세요","세안 후 스킨케어 마지막 단계에서 <b>적당량을 덜어 원하는 부위에 발라 흡수</b>시켜 주세요. 파운데이션 전에 소량을 섞어 바르는 분도 많아요."),
        10: T_("겨울철엔 굳을 수 있어요","호호바 오일은 온도가 낮으면 <b>하얗게 굳는 성질</b>이 있어요. 품질 이상이 아니에요. 실온에 두거나 따뜻한 물에 잠깐 담가 녹여 쓰세요.")}
def jpg(f): return R.jpeg(Image.open(f).convert("RGB"),90)
def files():
    return [os.path.join(D,"분할컷",f"호호바오일_{n:02d}.jpg") for n in SLICES]
def mains(key):
    fs=sorted(glob.glob(D+"/대표이미지*/thumb_0*.jpg"))
    return [(f"{key}-{i}.jpg",jpg(f)) for i,f in enumerate(fs[:7],1)]
def intro(cfg):
    ship="무료배송" if cfg["n"]>1 else "배송비 3,000원"; lab="50ml" if cfg["n"]==1 else f'50ml × {cfg["n"]}개 세트'
    return (f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;"><div style="font-size:22px;font-weight:700;color:{COLOR};">순유 Schön:u</div>'
            f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0;color:#111;">호호바오일</div><div style="font-size:30px;font-weight:800;color:#222;">{lab}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:10px;">{cfg["price"]:,}원 · <b style="color:{COLOR}">{ship}</b></div></div>')
def detail(cfg,urls):
    parts=[intro(cfg)]
    for i,u in enumerate(urls):
        parts.append(f'<img src="{u}" alt="순유 호호바오일" style="display:block;width:100%;height:auto;margin:0 auto;" />')
        if i in TEXT: parts.append(R.inline(TEXT[i],COLOR,BG))
    cfg2=dict(cfg,ship=0 if cfg["n"]>1 else 3000)
    parts.append(R.delivery(cfg2,COLOR))
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">'+"".join(parts)+"</div>"
CAUTION="1. 화장품 사용 시 또는 사용 후 직사광선에 의하여 사용부위가 붉은 반점, 부어오름 또는 가려움증 등의 이상 증상이나 부작용이 있는 경우에는 전문의 등과 상담할 것 2. 상처가 있는 부위 등에는 사용을 자제할 것 3. 보관 및 취급 시 주의사항 1) 어린이의 손이 닿지 않는 곳에 보관할 것 2) 직사광선을 피해서 보관할 것 4. 눈에 들어갔을 때에는 즉시 씻어낼 것"
def payload(key,cfg,mn,dt):
    fee=({"deliveryFeeType":"UNIT_QUANTITY_PAID","baseFee":cfg["ship"],"deliveryFeePayType":"PREPAID","repeatQuantity":1} if cfg["ship"] else {"deliveryFeeType":"FREE"})
    cap="50ml" if cfg["n"]==1 else f'50ml × {cfg["n"]}개'
    op={"statusType":"SALE","saleType":"NEW","leafCategoryId":CAT,"name":cfg["name"],"detailContent":dt,
        "images":{"representativeImage":{"url":mn[0]},"optionalImages":[{"url":u} for u in mn[1:9]]},"salePrice":cfg["price"],"stockQuantity":999,
        "deliveryInfo":{"deliveryType":"DELIVERY","deliveryAttributeType":"NORMAL","deliveryCompany":R.STORE.get("delivery_company","CJGLS"),"deliveryBundleGroupUsable":False,"deliveryFee":fee,
                        "claimDeliveryInfo":{"returnDeliveryFee":6000,"exchangeDeliveryFee":6000}},
        "detailAttribute":{"afterServiceInfo":{"afterServiceTelephoneNumber":R.STORE["after_service_telephone"],"afterServiceGuideContent":R.STORE["after_service_guide"]},
          "originAreaInfo":dict(originAreaCode="00",content="국산",plural=False),"minorPurchasable":True,"taxType":"TAX",
          "naverShoppingSearchInfo":{"brandName":"순유","manufacturerName":"(주)크레이지앤트","modelName":"순유 호호바오일"},"sellerCommentUsable":False,
          "productInfoProvidedNotice":{"productInfoProvidedNoticeType":"COSMETIC","cosmetic":{
              "capacity":cap,"specification":"호호바씨오일 100% 페이스 오일 (비정제·냉압착)","expirationDateText":"제조번호 및 사용기한은 제품에 별도 표기",
              "usage":"적당량을 덜어 원하는 부위에 발라 흡수시킵니다.","manufacturer":"(주)크레이지앤트","producer":"대한민국","distributor":"(주)크레이지앤트",
              "mainIngredient":"호호바씨오일 100%","certificationType":"해당없음(일반 화장품)","caution":CAUTION,
              "warrantyPolicy":"관련 법 및 소비자분쟁해결 규정에 따름","customerServicePhoneNumber":R.STORE["after_service_telephone"]}},
          "unitCapacity":{"unitPriceYn":True,"totalCapacityValue":50*cfg["n"],"unitCapacity":100,"indicationUnit":"ml"},
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
            cache=R.upload([(f"jj-{i:02d}.jpg",jpg(f)) for i,f in enumerate(files())]); print(f"[+] 상세 {len(cache)}조각",flush=True)
        r=R.post_with_retry(payload(key,cfg,R.upload(mains(key)),detail(cfg,cache)))
        if r.status_code!=200:
            print(f"[!] {key} {r.status_code}: {r.text[:900]}",flush=True); state[key]={"error":r.text[:900]}; STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); continue
        d=r.json(); state[key]={"productNo":d.get("smartstoreChannelProductNo") or d.get("productNo"),"originProductNo":d.get("originProductNo"),"price":cfg["price"]}
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); print(f"[+] {key} 등록 {state[key]['productNo']}",flush=True)
if __name__=="__main__": main()
