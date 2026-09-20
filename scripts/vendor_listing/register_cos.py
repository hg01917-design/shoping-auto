import glob, html, json, os, re, sys, time
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import register_new as R
from slicer import load_stack
Image.MAX_IMAGE_PIXELS = None
STATE = HERE / "등록결과_순유.json"
D = R.ROOT / "순유"
def num(f):
    m=re.findall(r'(\d+)',os.path.basename(f)); return int(m[-1]) if m else 0
def g(p): return sorted(glob.glob(str(D/p)),key=num)
CAUTION="1. 화장품 사용 시 또는 사용 후 직사광선에 의하여 사용부위가 붉은 반점, 부어오름 또는 가려움증 등의 이상 증상이나 부작용이 있는 경우에는 전문의 등과 상담할 것 2. 상처가 있는 부위 등에는 사용을 자제할 것 3. 보관 및 취급 시 주의사항 1) 어린이의 손이 닿지 않는 곳에 보관할 것 2) 직사광선을 피해서 보관할 것 4. 눈에 들어갔을 때에는 즉시 씻어낼 것"
P = {
 "오일": dict(cat="50000282", name0="릴렉싱 마사지 앤 바디오일", vol="200ml", cap=200, unit="ml", base=21900, sets={2:44900,3:66900}, color="#7B5EA7", bg="#F4EFFA",
   pname="순유 릴렉싱 마사지&바디오일", usage="샤워 후 물기가 남아있는 상태 또는 물기가 없는 상태에서 적당량을 덜어 마사지하듯 전신에 발라주며 흡수시킵니다.",
   ingr="상세 이미지의 제품정보 표 참조 (호호바씨오일, 스위트아몬드오일, 해바라기씨오일 등)", spec="마사지·바디 오일 (해피니스 / 스위트 드림 2종)", opts=["해피니스","스위트 드림"],
   names={1:"바디오일 마사지오일 순유 릴렉싱 마사지 앤 바디오일 200ml 해피니스 스위트드림 임산부",2:"순유 릴렉싱 마사지오일 200ml 2개 세트 바디오일 해피니스 스위트드림 무료배송",3:"바디오일 순유 릴렉싱 마사지 앤 바디오일 200ml 3개 세트 아로마 무료배송"},
   tags=["바디오일","마사지오일","바디마사지오일","천연바디오일","아로마마사지오일","바디오일추천","보습바디오일","임산부바디오일","아로마바디오일","순유"],
   pieces=lambda: g("1.*/상세페이지 분할 컷/*.jpg"),
   mains=lambda: sorted(glob.glob(str(D/"1.*/대표이미지(1000x1000px)/thumb_0[1-6].jpg")))+sorted(glob.glob(str(D/"1.*/대표이미지(1000x1000px)/thumb_0[78]*.jpg")))),
 "바디워시": dict(cat="50000285", name0="쿨 앤 스크럽 바디워시", vol="500ml", cap=500, unit="ml", base=24900, sets={2:50900,3:75900}, color="#3A8FC6", bg="#EEF6FC",
   pname="순유 쿨 앤 스크럽 바디워시", usage="적당량을 덜어 샤워 시 몸에 문지른 후 미지근한 물로 헹궈냅니다.", ingr="상세 이미지의 제품정보 표 참조 (정제수, 호두껍질분말 등)", spec="스크럽 입자 함유 쿨링 바디워시",
   names={1:"바디워시 순유 쿨 앤 스크럽 바디워시 500ml 여름 쿨링 바디스크럽",2:"쿨링 바디스크럽 워시 순유 쿨앤스크럽 바디워시 500ml 2개 세트 무료배송",3:"순유 쿨 앤 스크럽 바디워시 500ml 3개 세트 바디스크럽 쿨링 무료배송"},
   tags=["바디워시","바디스크럽","쿨링바디워시","여름바디워시","스크럽바디워시","남자바디워시","대용량바디워시","순유","바디클렌저","샤워"],
   pieces=lambda: g("5.*/분할컷/*.jpg"), mains=lambda: sorted(glob.glob(str(D/"5.*/대표이미지/thumb_0*.jpg")))),
 "페미닌폼": dict(cat="50000287", name0="퓨어 클린 페미닌 폼", vol="200ml", cap=200, unit="ml", base=16500, sets={2:33900,3:50900}, color="#D6577E", bg="#FDEFF3",
   pname="순유 퓨어 클린 페미닌 폼", usage="적당량을 덜어 외음부 주위에 사용한 후 깨끗이 씻어냅니다.", ingr="상세 이미지의 제품정보 표 참조 (정제수 등)", spec="여성 청결 폼 클렌저",
   names={1:"여성청결제 순유 퓨어 클린 페미닌 폼 200ml 여성 이너케어 거품형",2:"여성청결제 폼 순유 퓨어 클린 페미닌 폼 200ml 2개 세트 무료배송",3:"순유 퓨어 클린 페미닌 폼 200ml 3개 세트 여성청결제 거품 무료배송"},
   tags=["여성청결제","여성청결제추천","이너케어","여성청결제폼","거품형여성청결제","여성세정제","임산부여성청결제","페미닌워시","순유","여성케어"],
   pieces="fem", mains=lambda: sorted(glob.glob(str(D/"3.*/썸네일/00[1-8].jpg")))),
 "카밍밤": dict(cat="50000392", name0="멀티 카밍 밤", vol="15g", cap=15, unit="g", base=11900, sets={3:36900,5:61500}, color="#D9788A", bg="#FDF1F3",
   pname="순유 멀티 카밍 밤", usage="적당량을 덜어 원하는 부위에 얇게 펴 발라줍니다.", ingr="상세 이미지의 제품정보 표 참조 (비즈왁스, 호호바오일, 시어버터 등)", spec="멀티 보습 밤 15g",
   names={1:"멀티밤 순유 멀티 카밍 밤 15g 보습밤 립밤 핸드밤 건조한 피부",3:"순유 멀티 카밍 밤 15g 3개 세트 멀티밤 보습밤 무료배송",5:"멀티밤 보습밤 순유 멀티 카밍 밤 15g 5개 세트 무료배송"},
   tags=["멀티밤","보습밤","립밤","핸드밤","카밍밤","멀티보습밤","건조한피부","보습","순유","비즈왁스밤"],
   pieces="calm", mains=lambda: sorted(glob.glob(str(D/"슌윤*/대표이미지(1000x1000px)/멀티카밍밤-[123].jpg")))),
}
def pieces_of(k):
    p=P[k]["pieces"]
    if callable(p): return [Image.open(f).convert("RGB") for f in p()]
    if p=="fem":
        out=[]
        for f in g("3.*/상세페이지/*.jpg"):
            im=Image.open(f).convert("RGB"); out.append(im)
        st=Image.new("RGB",(860,sum(i.height for i in out)),"white"); y=0
        for i in out: st.paste(i,(0,y)); y+=i.height
        st=st.crop((0,0,860,st.height-(5712-4700)))   # 벤더 배송·교환 안내 제거
        return _auto(st)
    if p=="calm":
        fs=g("슌윤*/카밍밤 상세페이지 및 섬네일/카밍밤 상세 페이지/*.jpg")
        head=[Image.open(f).convert("RGB") for f in fs[:-3]]
        tail=[Image.open(f).convert("RGB") for f in fs[-3:]]
        st=Image.new("RGB",(860,sum(i.height for i in tail)),"white"); y=0
        for i in tail: st.paste(i.resize((860,i.height)) if i.width!=860 else i,(0,y)); y+=i.height
        return head+[st.crop((0,1560,860,st.height))]
def _auto(st):
    a=np.asarray(st); H=a.shape[0]; std=a.reshape(H,-1).astype(np.float32).std(axis=1)
    def blank(y,r=700):
        lo=max(1,y-r); hi=min(H-1,y+r); idx=[i for i in range(lo,hi) if std[i]<5]
        return min(idx,key=lambda i:abs(i-y)) if idx else lo+int(np.argmin(std[lo:hi]))
    cuts=[0]; y=0
    while H-y>2700:
        ny=blank(y+2000)
        if ny<=y+1000: ny=blank(y+2400)
        y=ny; cuts.append(y)
    cuts.append(H); return [st.crop((0,cuts[i],860,cuts[i+1])) for i in range(len(cuts)-1)]
def norm(im): return im.resize((860,int(im.height*860/im.width))) if im.width!=860 else im
def mains(key,k):
    out=[]
    for i,f in enumerate(P[k]["mains"]()[:9],1):
        im=Image.open(f).convert("RGB")
        if max(im.size)<800: im=im.resize((800,int(im.height*800/im.width)))
        out.append((f"{key}-{i}.jpg",R.jpeg(im,90)))
    return out
def intro(k,n,price,ship):
    p=P[k]; lab=p["vol"] if n==1 else f'{p["vol"]} × {n}개 세트'; sp="무료배송" if ship==0 else "배송비 3,000원"
    return (f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;"><div style="font-size:22px;font-weight:700;color:{p["color"]};">순유 Schön:u</div>'
            f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0;color:#111;">{p["name0"]}</div><div style="font-size:30px;font-weight:800;color:#222;">{lab}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:10px;">{price:,}원 · <b style="color:{p["color"]}">{sp}</b></div></div>')
def detail(k,n,price,ship,urls):
    p=P[k]; parts=[intro(k,n,price,ship)]+[f'<img src="{u}" alt="{p["pname"]}" style="display:block;width:100%;height:auto;margin:0 auto;" />' for u in urls]
    parts.append(R.delivery(dict(ship=ship),p["color"]))
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">'+"".join(parts)+"</div>"
def payload(k,n,price,ship,name,tags,mn,dt):
    p=P[k]; fee=({"deliveryFeeType":"UNIT_QUANTITY_PAID","baseFee":ship,"deliveryFeePayType":"PREPAID","repeatQuantity":1} if ship else {"deliveryFeeType":"FREE"})
    cap=p["vol"] if n==1 else f'{p["vol"]} × {n}개'
    op={"statusType":"SALE","saleType":"NEW","leafCategoryId":p["cat"],"name":name,"detailContent":dt,
        "images":{"representativeImage":{"url":mn[0]},"optionalImages":[{"url":u} for u in mn[1:9]]},"salePrice":price,"stockQuantity":999,
        "deliveryInfo":{"deliveryType":"DELIVERY","deliveryAttributeType":"NORMAL","deliveryCompany":R.STORE.get("delivery_company","CJGLS"),"deliveryBundleGroupUsable":False,"deliveryFee":fee,"claimDeliveryInfo":{"returnDeliveryFee":6000,"exchangeDeliveryFee":6000}},
        "detailAttribute":{"afterServiceInfo":{"afterServiceTelephoneNumber":R.STORE["after_service_telephone"],"afterServiceGuideContent":R.STORE["after_service_guide"]},
          "originAreaInfo":dict(originAreaCode="00",content="국산",plural=False),"minorPurchasable":True,"taxType":"TAX",
          "naverShoppingSearchInfo":{"brandName":"순유","manufacturerName":"(주)크레이지앤트","modelName":p["pname"]},"sellerCommentUsable":False,
          "productInfoProvidedNotice":{"productInfoProvidedNoticeType":"COSMETIC","cosmetic":{"capacity":cap,"specification":p["spec"],"expirationDateText":"제조번호 및 사용기한은 제품에 별도 표기",
              "usage":p["usage"],"manufacturer":"(주)크레이지앤트","producer":"대한민국","distributor":"(주)크레이지앤트","mainIngredient":p["ingr"],"certificationType":"해당없음(일반 화장품)",
              "caution":CAUTION,"warrantyPolicy":"관련 법 및 소비자분쟁해결 규정에 따름","customerServicePhoneNumber":R.STORE["after_service_telephone"]}},
          "unitCapacity":{"unitPriceYn":True,"totalCapacityValue":p["cap"]*n,"unitCapacity":100 if p["unit"]=="ml" else 10,"indicationUnit":p["unit"]},
          "certificationTargetExcludeContent":{"childCertifiedProductExclusionYn":True,"kcCertifiedProductExclusionYn":"TRUE","greenCertifiedProductExclusionYn":True},
          "seoInfo":{"sellerTags":[{"text":t} for t in tags]}}}
    if p.get("opts") and True:
        op["detailAttribute"]["optionInfo"]={"optionCombinationSortType":"CREATE","optionCombinationGroupNames":{"optionGroupName1":"향"},
          "optionCombinations":[{"optionName1":o,"stockQuantity":999,"price":0,"usable":True} for o in p["opts"]],"useStockManagement":True}
    return {"originProduct":op,"smartstoreChannelProduct":{"naverShoppingRegistration":True,"channelProductDisplayStatusType":"ON"}}

P["노즈밤"]=dict(cat="50000392", name0="모이스처 노즈밤", vol="15g", cap=15, unit="g", base=11900, sets={3:36900,5:61500}, color="#3E8FD1", bg="#EEF6FD",
   pname="순유 모이스처 노즈밤", usage="적당량을 덜어 코 주변에 얇게 펴 발라줍니다.", ingr="상세 이미지의 제품정보 표 참조 (비즈왁스, 유칼립투스잎오일 등)", spec="코 주변 보습 밤 15g",
   names={1:"코 보습 밤 순유 모이스처 노즈밤 15g 코주변 건조 보습 아기 온가족",3:"순유 모이스처 노즈밤 15g 3개 세트 코보습밤 건조 무료배송",5:"코보습 노즈밤 순유 모이스처 노즈밤 15g 5개 세트 무료배송"},
   tags=["노즈밤","코보습밤","코주변보습","보습밤","건조한피부","순유","아기보습","멀티밤","코건조","유칼립투스"],
   pieces="nose", mains=lambda: sorted(glob.glob(str(D/"슌윤*/대표이미지(1000x1000px)/모이스처 노즈밤-[1-7].jpg")))[:7])
P["바디솝"]=dict(cat="50000288", name0="쿨링 바디솝", vol="90g", cap=90, unit="g", base=8900, sets={3:27900,5:46500}, color="#B8B23A", bg="#FBFAE3",
   pname="순유 쿨링 바디솝", usage="물에 적신 후 거품을 내어 몸에 사용하고 깨끗이 헹궈냅니다.", ingr="제품 포장의 전성분 표기 참조", spec="쿨링 바디 비누 90g",
   names={1:"바디비누 순유 쿨링 바디솝 90g 시원한 여름 바디솝 레몬향",3:"순유 쿨링 바디솝 90g 3개 세트 바디비누 여름 쿨링 무료배송",5:"쿨링 바디비누 순유 바디솝 90g 5개 세트 무료배송"},
   tags=["바디솝","바디비누","쿨링바디솝","여름바디솝","목욕비누","쿨링비누","레몬비누","순유","바디클렌저","쿨링"],
   pieces=lambda: sorted(glob.glob(str(D/"7*/바디솝상세페이지/*.jpg")),key=lambda f:(0 if re.search(r"133\.jpg$",f) else 1, num(f))),
   mains=lambda: sorted(glob.glob(str(D/"7*/바디솝대표이미지/*.jpg"))))
P["스프레이"]=dict(cat="50002693", name0="내츄럴 허벌 스프레이", vol="100ml", cap=100, unit="ml", base=13500, sets={2:27700,3:41900}, color="#4F8A5B", bg="#EFF7F0", opts=["허브가든","딥포레스트"],
   pname="순유 내츄럴 허벌 스프레이", usage="", ingr="", spec="", bio=True,
   names={1:"순유 내츄럴 허벌 스프레이 100ml 허브가든 딥포레스트 아로마 모기 스프레이",2:"내츄럴 허벌 스프레이 100ml 2개 세트 순유 아로마 스프레이 무료배송",3:"순유 내츄럴 허벌 스프레이 100ml 3개 세트 허브가든 딥포레스트 무료배송"},
   tags=["허벌스프레이","아로마스프레이","천연스프레이","모기스프레이","벌레퇴치","여름스프레이","순유","캠핑스프레이","아기스프레이","시트로넬라"],
   pieces=lambda: sorted(glob.glob(str(D/"6.*/내츄럴*/상세페이지 분할컷/*.jpg")),key=num),
   mains=lambda: sorted(glob.glob(str(D/"6.*/대표이미지/thumb_0[1-5].jpg")))+sorted(glob.glob(str(D/"6.*/대표이미지/thumb_0[67]*.jpg"))))
_old_pieces=pieces_of
def pieces_of(k):
    if P[k]["pieces"]=="nose":
        f=glob.glob(str(D/"슌윤*/모이스처노즈밤 상세페이지/모이스처노즈밤-수정.jpg"))[0]
        return _auto(Image.open(f).convert("RGB"))
    return _old_pieces(k)
_old_payload=payload
def payload(k,n,price,ship,name,tags,mn,dt):
    pl=_old_payload(k,n,price,ship,name,tags,mn,dt)
    if P[k].get("bio"):
        da=pl["originProduct"]["detailAttribute"]; wt="100ml"+(f" × {n}개" if n>1 else "")
        da["productInfoProvidedNotice"]={"productInfoProvidedNoticeType":"BIOCHEMISTRY","biochemistry":{
            "productName":"순유 내츄럴 허벌 스프레이 (생활화학제품 기피제)","dosageForm":"스프레이형 (모기·벌레 기피 아로마)","packDateText":"제품에 별도 표기","expirationDateText":"제조일로부터 2년",
            "weight":wt,"effect":"모기 등 벌레 기피 보조 (아로마 성분)","producer":"대한민국","manufacturer":"(주)크레이지앤트","childProtection":"해당없음",
            "chemicals":"시트로넬라, 페니로열, 라벤더, 유칼립투스, 티트리, 로즈마리 등 아로마 오일 (상세 이미지 참조)",
            "caution":"1. 피부 자극 반응 시 사용을 중단할 것 2. 내용물을 먹거나 삼킨 경우 즉시 의사와 상담할 것 3. 눈에 들어갔을 경우 깨끗한 물로 씻어낼 것 4. 어린이 손이 닿지 않는 곳에 보관할 것 5. 직사광선을 피해 서늘한 곳에 보관할 것",
            "safeCriterionNo":"제HB22-23-0009호 (안전기준 적합확인 신고)","customerServicePhoneNumber":R.STORE["after_service_telephone"]}}
        da.pop("unitCapacity",None)
    return pl

def main():
    only=sys.argv[1:] ; state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    for k,p in P.items():
        if only and k not in only: continue
        urls=None
        for n,price in [(1,p["base"])]+sorted(p["sets"].items()):
            key=f"{k}-{n}"
            if state.get(key,{}).get("productNo"): print("[=]",key); continue
            if urls is None:
                urls=R.upload([(f"{k}-{i:02d}.jpg",R.jpeg(norm(im))) for i,im in enumerate(pieces_of(k))]); print(f"[+] {k} 상세 {len(urls)}조각",flush=True)
            ship=3000 if n==1 else 0
            r=R.post_with_retry(payload(k,n,price,ship,p["names"][n],p["tags"],R.upload(mains(key,k)),detail(k,n,price,ship,urls)))
            if r.status_code!=200:
                print(f"[!] {key} {r.status_code}: {r.text[:700]}",flush=True); state[key]={"error":r.text[:700]}; STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); continue
            d=r.json(); state[key]={"productNo":d.get("smartstoreChannelProductNo") or d.get("productNo"),"originProductNo":d.get("originProductNo"),"price":price}
            STATE.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding="utf-8"); print(f"[+] {key} 등록 {state[key]['productNo']}",flush=True)
if __name__=="__main__": main()
