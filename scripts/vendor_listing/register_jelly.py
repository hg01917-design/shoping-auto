import glob, html, json, os, sys, time
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import register_new as R
from slicer import load_stack
Image.MAX_IMAGE_PIXELS = None
STATE = HERE / "등록결과_젤리.json"
D = R.ROOT / "슬릭스홍삼"
CAT = "50022479"
FAM = {
 "슬릭스": dict(color="#6B3FB0", bg="#F3EEFB", brand="싸락", model="슬릭스 젤리스틱 30포", pname="슬릭스 다이어트 젤리", w=780,
     detail=str(D/"슬릭스_상페"/"(쿠팡size780)슬릭스_상페_all.jpg"), mains=[("슬릭스_썸네일","KakaoTalk_20260220_164843625.jpg"),("슬릭스_썸네일","KakaoTalk_20260220_164843625_01.jpg"),("슬릭스_썸네일","KakaoTalk_20260220_164843625_02.jpg"),("슬릭스_썸네일","리스트_슬릭스-1.jpg"),("슬릭스_썸네일","리스트_슬릭스-4.jpg"),("슬릭스_썸네일","리스트_슬릭스-6.jpg")],
     report="202501864092", ingr="옥수수염추출물(까마중, 건조대두, 검정팥, 대추, 대나무잎(한국), 옥수수수염, 맥아, 갈근(중국), 생강), 석류농축액(터키), 석류향, 난소화성덱스트린, 가르시니아(인도), 구연산, 비타민C, 효소스테비아, 젖산칼슘, 피쉬콜라겐(베트남)",
     nutri="1포(20g)당 열량 15kcal, 나트륨 0~3mg, 지방 0~0.1g, 트랜스지방 0g (자세한 영양정보는 제품 라벨 참조)"),
 "홍삼콜라겐": dict(color="#B3202A", bg="#FCEEEE", brand="싸락", model="싸락 홍삼콜라겐 젤리스틱 30포", pname="홍삼콜라겐 젤리", w=780,
     detail=str(D/"홍삼콜라겐_상페"/"KakaoTalk_20260223_124855420_02.jpg"), mains=[("홍삼콜라겐_썸네일","리스트_홍삼콜라겐-2.jpg"),("홍삼콜라겐_썸네일","리스트_홍삼콜라겐-3.jpg"),("홍삼콜라겐_썸네일","리스트_홍삼콜라겐-6.jpg"),("홍삼콜라겐_썸네일","리스트_홍삼콜라겐-7.jpg"),("홍삼콜라겐_썸네일","리스트_홍삼콜라겐-8.jpg"),("홍삼콜라겐_썸네일","리스트_홍삼콜라겐-1.jpg")],
     report="2019015065217", ingr="홍삼농축액(7ppm), 홍삼추출물, 인삼추출물, 사양꿀, 저당피쉬콜라겐(베트남), 구연산, 홍삼향, 스테비아, 하리겔c, 흙설탕, 덱스트린, 기타가공품",
     nutri="1포(20g)당 열량 26kcal, 나트륨 15mg, 탄수화물 6g(당류 5g), 단백질 1g, 지방 0g, 트랜스지방 0g, 포화지방 0g, 콜레스테롤 0mg"),
}
L = {}
for fam,tags1,name1,name2,name3 in [
 ("슬릭스",["젤리스틱","석류젤리","석류젤리스틱","식이섬유젤리","스틱젤리","건강젤리","짜먹는젤리","콜라겐젤리","싸락젤리","슬릭스"],
   "싸락 슬릭스 젤리스틱 30포 석류맛 식이섬유 콜라겐 스틱젤리","슬릭스 젤리스틱 30포 2개 세트 석류 식이섬유 스틱젤리 무료배송","싸락 슬릭스 젤리스틱 30포 3개 세트 석류맛 스틱젤리 무료배송"),
 ("홍삼콜라겐",["홍삼젤리","콜라겐젤리","홍삼젤리스틱","콜라겐스틱","석류콜라겐","먹는콜라겐젤리","선물세트","건강젤리","젤리스틱","싸락"],
   "싸락 홍삼콜라겐 젤리스틱 30포 홍삼젤리 콜라겐 스틱젤리","홍삼콜라겐 젤리 30포 2개 세트 홍삼젤리스틱 콜라겐스틱 무료배송","싸락 홍삼콜라겐 젤리스틱 30포 3개 세트 홍삼젤리 선물세트 무료배송")]:
    L[f"{fam}-단품"]=dict(fam=fam,n=1,price=30900,ship=3000,name=name1,tags=tags1)
    L[f"{fam}-2개"]=dict(fam=fam,n=2,price=62900,ship=0,name=name2,tags=[t for t in tags1[::-1]][:10])
    L[f"{fam}-3개"]=dict(fam=fam,n=3,price=93900,ship=0,name=name3,tags=tags1[2:]+tags1[:2])
def slices(fam):
    f=FAM[fam]; st,_=load_stack([f["detail"]]); a=np.asarray(st); H=a.shape[0]; std=a.reshape(H,-1).astype(np.float32).std(axis=1)
    def blank(y,r=700):
        lo=max(1,y-r); hi=min(H-1,y+r); idx=[i for i in range(lo,hi) if std[i]<5]
        return min(idx,key=lambda i:abs(i-y)) if idx else lo+int(np.argmin(std[lo:hi]))
    cuts=[0]; y=0
    while H-y>2700:
        ny=blank(y+2000)
        if ny<=y+1000: ny=blank(y+2400)
        y=ny; cuts.append(y)
    cuts.append(H); return [st.crop((0,cuts[i],860,cuts[i+1])) for i in range(len(cuts)-1)]
def mains(key,fam):
    out=[]
    for i,(d,f) in enumerate(FAM[fam]["mains"],1):
        im=Image.open(D/d/f).convert("RGB")
        if max(im.size)<800: im=im.resize((800,800))
        out.append((f"{key}-{i}.jpg",R.jpeg(im,90)))
    return out
def intro(cfg):
    f=FAM[cfg["fam"]]; ship="무료배송" if cfg["n"]>1 else "배송비 3,000원"; lab="30포 (20g × 30)" if cfg["n"]==1 else f'30포 × {cfg["n"]}박스'
    return (f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;"><div style="font-size:22px;font-weight:700;color:{f["color"]};">싸락 Ssarak</div>'
            f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0;color:#111;">{f["pname"]}</div><div style="font-size:30px;font-weight:800;color:#222;">{lab}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:10px;">{cfg["price"]:,}원 · <b style="color:{f["color"]}">{ship}</b></div></div>')
def detail(cfg,urls):
    f=FAM[cfg["fam"]]; parts=[intro(cfg)]
    for u in urls: parts.append(f'<img src="{u}" alt="{f["pname"]}" style="display:block;width:100%;height:auto;margin:0 auto;" />')
    parts.append(R.delivery(dict(cfg,ship=0 if cfg["n"]>1 else 3000),f["color"]))
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">'+"".join(parts)+"</div>"
def payload(key,cfg,mn,dt):
    f=FAM[cfg["fam"]]
    fee=({"deliveryFeeType":"UNIT_QUANTITY_PAID","baseFee":cfg["ship"],"deliveryFeePayType":"PREPAID","repeatQuantity":1} if cfg["ship"] else {"deliveryFeeType":"FREE"})
    wt=f'20g × 30포' + (f' × {cfg["n"]}박스' if cfg["n"]>1 else '')
    op={"statusType":"SALE","saleType":"NEW","leafCategoryId":CAT,"name":cfg["name"],"detailContent":dt,
        "images":{"representativeImage":{"url":mn[0]},"optionalImages":[{"url":u} for u in mn[1:9]]},"salePrice":cfg["price"],"stockQuantity":999,
        "deliveryInfo":{"deliveryType":"DELIVERY","deliveryAttributeType":"NORMAL","deliveryCompany":R.STORE.get("delivery_company","CJGLS"),"deliveryBundleGroupUsable":False,"deliveryFee":fee,
                        "claimDeliveryInfo":{"returnDeliveryFee":6000,"exchangeDeliveryFee":6000}},
        "detailAttribute":{"afterServiceInfo":{"afterServiceTelephoneNumber":R.STORE["after_service_telephone"],"afterServiceGuideContent":R.STORE["after_service_guide"]},
          "originAreaInfo":dict(originAreaCode="00",content="국산",plural=False),"minorPurchasable":True,"taxType":"TAX",
          "naverShoppingSearchInfo":{"brandName":f["brand"],"manufacturerName":"(주)싸락","modelName":f["model"]},"sellerCommentUsable":False,
          "productInfoProvidedNotice":{"productInfoProvidedNoticeType":"GENERAL_FOOD","generalFood":{
              "productName":f["pname"],"foodType":"캔디류(젤리)","producer":"(주)싸락 (유통전문판매원 (주)엠에스명성바이오)","location":"부산시 남구 신선로 365 부경대학교 용당캠퍼스 용당5관 301호",
              "packDateText":"제품 포장에 별도 표시","consumptionDateText":"제조일로부터 24개월","weight":wt,"amount":wt,"ingredients":f["ingr"],"nutritionFacts":f["nutri"],
              "geneticallyModified":False,"consumerSafetyCaution":"임산부는 섭취에 주의하시기 바랍니다. 전자레인지에 직접 넣어 데우지 마십시오. 알레르기 체질일 경우 원재료 확인 후 섭취하십시오. 직사광선과 고온다습한 곳을 피하고 어린이의 손이 닿지 않는 곳에 보관하십시오. 부정·불량식품 신고는 국번없이 1399",
              "importDeclarationCheck":False,"customerServicePhoneNumber":"051-893-1553"}},
          "unitCapacity":{"unitPriceYn":True,"totalCapacityValue":600*cfg["n"],"unitCapacity":100,"indicationUnit":"g"},
          "certificationTargetExcludeContent":{"childCertifiedProductExclusionYn":True,"kcCertifiedProductExclusionYn":"TRUE","greenCertifiedProductExclusionYn":True},
          "seoInfo":{"sellerTags":[{"text":t} for t in cfg["tags"]]}}}
    return {"originProduct":op,"smartstoreChannelProduct":{"naverShoppingRegistration":True,"channelProductDisplayStatusType":"ON"}}
def main():
    only=sys.argv[1] if len(sys.argv)>1 else None
    state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}; cache={}
    for key,cfg in L.items():
        if only and only!=key: continue
        if state.get(key,{}).get("productNo"): print("[=]",key); continue
        fam=cfg["fam"]
        if fam not in cache:
            cache[fam]=R.upload([(f"{fam}-{i:02d}.jpg",R.jpeg(im)) for i,im in enumerate(slices(fam))]); print(f"[+] {fam} 상세 {len(cache[fam])}조각",flush=True)
        r=R.post_with_retry(payload(key,cfg,R.upload(mains(key,fam)),detail(cfg,cache[fam])))
        if r.status_code!=200:
            print(f"[!] {key} {r.status_code}: {r.text[:900]}",flush=True); state[key]={"error":r.text[:900]}; STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); continue
        d=r.json(); state[key]={"productNo":d.get("smartstoreChannelProductNo") or d.get("productNo"),"originProductNo":d.get("originProductNo"),"price":cfg["price"]}
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); print(f"[+] {key} 등록 {state[key]['productNo']}",flush=True)
if __name__=="__main__": main()
