"""벤더 신규상품(폭싹 눈찜질팩, 세안타올) 스마트스토어 등록.

  python3 register_new.py --dry
  python3 register_new.py --only 폭싹-단품
  python3 register_new.py
"""
import argparse, glob, html, io, json, os, re, sys, time
from datetime import datetime
from pathlib import Path

import numpy as np
import requests
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHOP = ROOT.parent / "shoping-auto"
sys.path.insert(0, str(SHOP / "scripts"))
sys.path.insert(0, str(HERE))
from naver_auth import API_BASE, auth_headers  # noqa: E402
from slicer import load_stack, W  # noqa: E402

STORE = json.loads((SHOP / "config" / "store.json").read_text(encoding="utf-8"))
CUTS = json.loads((HERE / "cuts.json").read_text(encoding="utf-8"))
STATE = HERE / "등록결과.json"
IMG_URL = f"{API_BASE}/v1/product-images/upload"
PROD_URL = f"{API_BASE}/v2/products"

PS = ROOT / "폭싹속았수다"
TW = ROOT / "세안타올"
PS_TH = glob.glob(str(PS / "*" / "*썸네일*"))[0]
TW_DIR = glob.glob(str(TW / "오일팡*"))[0]

# ------------------------------------------------------------------ 상품 정의
FAM = {
    "폭싹": dict(color="#C9793A", bg="#FFF5E8", brand="들꽃잠", maker="들꽃잠", model="폭싹속았수다 눈찜질팩",
                 item="들꽃잠 폭싹속았수다 눈찜질팩", origin=dict(originAreaCode="00", content="국산", plural=False),
                 cert="해당없음(일반 공산품)"),
    "타올": dict(color="#3E7D5A", bg="#F1F7F2", brand="내일봄", maker="오일팡(OILPANG CO LTD)", model="내일봄 페이스 크리너 타올",
                 item="내일봄 페이스 크리너 타올 (세안타올)", origin=dict(originAreaCode="0008", content="국산:부산광역시", plural=False),
                 cert="해당없음(일반 공산품)"),
}

PS_OPT_1 = ["숯 (폭싹속았수다)", "황토 (소랑햄수다)"]
PS_OPT_2 = ["숯 2개", "황토 2개", "숯 1개 + 황토 1개"]
PS_OPT_3 = ["숯 3개", "황토 3개", "숯 2개 + 황토 1개", "숯 1개 + 황토 2개"]

LISTINGS = {
    "폭싹-단품": dict(fam="폭싹", cat="50001932", price=45000, ship=3000,
        name="눈찜질팩 들꽃잠 폭싹속았수다 팥 온열 눈찜질안대 전자레인지 찜질", opts=PS_OPT_1, optgroup="색상", thumbs=[1, 2, 3, 4, 5, 6, 7],
        tags=["눈찜질팩", "황토찜질팩", "팥찜질팩", "눈찜질안대", "눈온열안대", "전자레인지찜질팩", "눈찜질", "온찜질팩", "눈안대", "들꽃잠"],
        hook="하루 끝, 눈에게도 따뜻한 쉼표를"),
    "폭싹-2개": dict(fam="폭싹", cat="50001819", price=92900, ship=0,
        name="온열안대 팥찜질팩 들꽃잠 폭싹속았수다 눈찜질팩 2개 세트 무료배송", opts=PS_OPT_2, optgroup="구성", thumbs=[3, 6, 1, 4, 5, 2, 7],
        tags=["온열안대", "온열수면안대", "찜질안대", "눈찜질기", "눈온열찜질기", "온열아이마스크", "선물세트", "부모님선물", "눈찜질팩2개", "폭싹속았수다"],
        hook="두 개면 하나는 선물"),
    "폭싹-3개": dict(fam="폭싹", cat="50001932", price=137900, ship=0,
        name="황토 눈찜질팩 전자레인지 온열 눈찜질안대 들꽃잠 3개 세트 무료배송", opts=PS_OPT_3, optgroup="구성", thumbs=[4, 5, 2, 6, 1, 3, 7],
        tags=["찜질팩", "온찜질팩", "냉온찜질팩", "온열팩", "냉찜질팩", "황토눈찜질", "눈찜질팩3개", "가족선물", "명절선물", "소랑햄수다"],
        hook="온 가족이 나눠 쓰는 넉넉한 구성"),
    "타올-소형5": dict(fam="타올", cat="50004392", price=32900, ship=0, variant="소형", qty="소형 5개",
        name="세안타올 클렌징타올 페이스타올 극세사 내일봄 소형 5개 세트 무료배송", opts=None,
        thumbs=[16, 18, 24, 26, 25], tags=["세안타올", "클렌징타올", "페이스타올", "극세사타올", "세안도구", "얼굴타올", "클렌징패드", "화장지우개", "내일봄", "페이스클리너"]),
    "타올-소형10": dict(fam="타올", cat="50004392", price=64900, ship=0, variant="소형", qty="소형 10개",
        name="극세사 세안타올 10개 클렌징타올 페이스타올 내일봄 소형 대용량 무료배송", opts=None,
        thumbs=[18, 21, 23, 25, 24], tags=["극세사세안타올", "세안타올10개", "클렌징타올", "페이스타올", "타올대용량", "얼굴세안타올", "세안패드", "메이크업클렌징", "내일봄타올", "페이스타월"]),
    "타올-중형3": dict(fam="타올", cat="50004392", price=38900, ship=0, variant="중형", qty="중형 3개",
        name="내일봄 페이스 크리너 타올 중형 3개 세안타올 클렌징타올 무료배송", opts=None,
        thumbs=[21, 16, 26, 24, 23], tags=["페이스타올", "세안타올중형", "클렌징타올", "얼굴수건", "세안수건", "극세사수건", "세안도구", "타올3개", "화장솜대용", "페이스크리너"]),
    "타올-중형5": dict(fam="타올", cat="50004392", price=64900, ship=0, variant="중형", qty="중형 5개",
        name="클렌징타올 세안타올 극세사 페이스타올 중형 5개 내일봄 무료배송", opts=None,
        thumbs=[23, 25, 18, 16, 21], tags=["클렌징타올", "세안타올5개", "극세사타올", "페이스타월", "얼굴타올", "세안패드", "세안수건", "메이크업지우개", "타올세트", "세안타올세트"]),
    "타올-혼합": dict(fam="타올", cat="50004392", price=45900, ship=0, variant="소형 중형 같이", qty="소형 3개 + 중형 2개",
        name="세안타올 소형 3개 중형 2개 세트 클렌징타올 페이스타올 내일봄 무료배송", opts=None,
        thumbs=[24, 26, 21, 16, 23], tags=["세안타올세트", "소형중형세트", "클렌징타올", "페이스타올", "극세사세안타올", "얼굴타올", "세안도구", "세안패드", "내일봄", "타올선물"]),
}

# ------------------------------------------------------------------ 상세 텍스트
def T(h, *ps, small=None):
    s = '<div class="t">'
    if h: s += f"<h2>{h}</h2>"
    for p in ps: s += f"<p>{p}</p>"
    if small: s += f"<small>{small}</small>"
    return s + "</div>"

PS_TEXT = {  # 조각 인덱스 뒤에 삽입
    2: T("폭싹 속았수다, 오늘 하루도", "일도 집안일도 눈으로 다 보고 나면, 저녁엔 눈도 좀 쉬고 싶죠.", "들꽃잠 <b>폭싹속았수다 눈찜질팩</b>은 팥을 넣어 전자레인지에 데워 쓰는 찜질팩이에요. 이름만 봐도 위로가 되는 제주 말투가 눈에 띄는 제품입니다."),
    8: T("색은 두 가지, 마음은 하나", "차분한 <b>숯 색 '폭싹속았수다'</b>와 따뜻한 <b>황토 색 '소랑햄수다'</b> 중에서 고를 수 있어요. 받는 분의 분위기에 맞춰 골라 보세요."),
    10: T("특징만 콕 짚으면", "<b>팥 100%(가공팥)</b>을 채운 <b>면 100% 겉감</b>, 그리고 전자레인지로 간단히 데우는 방식이에요. 눈 위에 올려 두는 편안한 무게감도 있어요."),
    13: T("크기와 정보, 미리 확인하세요", "사이즈는 <b>255 × 125mm</b>이고, 국내에서 만든 제품이에요. 색상은 숯(폭싹속았수다)과 황토(소랑햄수다) 두 가지입니다.", small="※ 위 정보는 상세 이미지의 제품정보고시를 기준으로 했어요."),
    19: T("만든 곳도 궁금하시죠", "들꽃잠은 <b>팥 가공 기술</b>과 <b>원단 안전성 시험</b> 자료를 함께 안내하고 있어요. 직접 눈에 올리는 제품이라 더 꼼꼼하게 챙겼습니다."),
    26: T("데우는 방법은 이렇게", "<b>전자레인지에 여름 약 40초, 겨울 약 50초</b>가 기본이에요. 처음엔 짧게 데우고, 너무 뜨겁지 않은지 확인한 뒤 사용해 주세요.", small="※ 전자레인지 출력에 따라 시간이 달라질 수 있어요. 과열에 주의해 주세요."),
    29: T("선물로도 좋아요", "고급스러운 디자인의 포장 상자에 담겨 있어서 <b>부모님, 친구, 동료 선물</b>로 많이 찾는 제품이에요."),
}
TW_TEXT = {
    1: T("세안, 이렇게 가볍게", "비누나 폼으로 씻고 나서 <b>부드러운 극세사 타올</b>로 슥슥. 손바닥 안에 쏙 들어오는 작은 사이즈라 <b>세면대 옆에 두고 쓰기 좋아요</b>."),
    4: T("소형 8×9cm, 중형 11×12cm", "얼굴과 손 크기에 맞게 <b>소형(8×9cm)</b>과 <b>중형(11×12cm)</b> 두 가지 크기가 있어요. 이 상품의 구성은 아래 정보에서 다시 한번 확인해 주세요."),
    7: T("독일 더마테스트 인증 자료가 있어요", "<b>독일 더마테스트(Dermatest) 'Excellent' 등급</b> 시험 성적서와 한국의류시험연구원 시험 자료가 상세 이미지에 들어 있어요. 궁금하신 분은 직접 확인해 보세요.", small="※ 시험 결과는 제조사가 제공한 자료이며, 개인에 따라 다를 수 있습니다."),
}

# ------------------------------------------------------------------ 이미지
def jpeg(im, q=88):
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=q, optimize=True); return b.getvalue()

def upload(files):
    urls = []
    for i in range(0, len(files), 5):
        ch = files[i:i + 5]
        payload = [("imageFiles", (n, d, "image/jpeg")) for n, d in ch]
        for attempt in range(3):
            r = requests.post(IMG_URL, headers=auth_headers(), files=payload, timeout=240)
            if r.status_code == 200: break
            time.sleep(2)
        if r.status_code != 200: raise RuntimeError(f"업로드 실패 {r.status_code}: {r.text[:300]}")
        got = [x["url"] for x in r.json().get("images", [])]
        if len(got) != len(ch): raise RuntimeError("업로드 개수 불일치")
        urls += got; time.sleep(0.5)
    return urls

def detail_slices(fam, variant=None):
    if fam == "폭싹":
        files = [str(ROOT / f) for f in CUTS["ps_files"]]; cuts = CUTS["ps"]
        st, _ = load_stack(files)
    else:
        f = glob.glob(os.path.join(TW_DIR, f"{variant}.jpg"))[0]
        st, _ = load_stack([f]); cuts = CUTS["tw"]
    return [st.crop((0, cuts[i], W, cuts[i + 1])) for i in range(len(cuts) - 1)]

def main_images(key, cfg):
    if cfg["fam"] == "폭싹":
        files = sorted(glob.glob(PS_TH + "/*.jpg"), key=lambda f: (0 if re.search(r"썸네일600\.jpg$", f) else 1, f))
        paths = [files[i - 1] for i in cfg["thumbs"] if i - 1 < len(files)]
    else:
        allf = sorted(glob.glob(str(TW / "썸네일" / "*")) ) + sorted(glob.glob(os.path.join(TW_DIR, "대표이미지", "*")))
        # 번호는 contact sheet 기준(썸네일 0~15, 대표이미지 16~)
        th = sorted(glob.glob(str(TW / "썸네일" / "*.jpg"))) + sorted(glob.glob(str(TW / "썸네일" / "*.png")))
        rp = sorted(glob.glob(os.path.join(TW_DIR, "대표이미지", "*")))
        seq = th + rp
        paths = [seq[i] for i in cfg["thumbs"]]
    out = []
    for i, p in enumerate(paths[:5], 1):
        im = Image.open(p).convert("RGB")
        m = max(im.size)
        c = Image.new("RGB", (max(m, 800), max(m, 800)), "white")
        sc = 1.0 if m >= 800 else 800 / m
        im2 = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS) if sc != 1.0 else im
        c = Image.new("RGB", (max(im2.size), max(im2.size)), "white")
        c.paste(im2, ((c.width - im2.width) // 2, (c.height - im2.height) // 2))
        out.append((f"{key}-{i}.jpg", jpeg(c, 90)))
    return out

# ------------------------------------------------------------------ 상세 HTML
def inline(s, color, bg):
    s = s.replace('<div class="t">', f'<div style="padding:56px 44px;color:#333;background:{bg};text-align:left;word-break:keep-all;">')
    s = s.replace("<h2>", f'<h2 style="font-size:32px;line-height:1.45;margin:0 0 22px;color:#222;border-left:9px solid {color};padding-left:16px;font-weight:800;">')
    s = s.replace("<p>", '<p style="margin:0 0 16px;font-size:22px;line-height:1.8;">')
    s = s.replace("<b>", f'<b style="background:linear-gradient(transparent 60%,{color}55 60%);font-weight:800;">')
    s = s.replace("<small>", '<small style="display:block;font-size:17px;color:#777;line-height:1.6;">')
    return s

def intro(key, cfg):
    f = FAM[cfg["fam"]]; c = f["color"]
    price = f"{cfg['price']:,}원"
    if cfg["fam"] == "폭싹":
        label = {"단품": "1개", "2개": "2개 세트", "3개": "3개 세트"}[key.split("-")[1]]
        title = "폭싹속았수다 눈찜질팩"; sub = "들꽃잠 · 팥 찜질 · 전자레인지용"
    else:
        label = cfg["qty"] + " 구성"; title = "내일봄 페이스 크리너 타올"; sub = "극세사 세안타올 · 소형 8×9cm / 중형 11×12cm"
    ship = "무료배송" if cfg["ship"] == 0 else "배송비 3,000원"
    return (f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;">'
            f'<div style="font-size:22px;font-weight:700;color:{c};">{html.escape(f["brand"])}</div>'
            f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0 14px;color:#111;word-break:keep-all;">{title}</div>'
            f'<div style="font-size:24px;color:#666;margin-bottom:22px;">{sub}</div>'
            f'<div style="font-size:32px;font-weight:800;color:#222;">{label}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:10px;">{price} · <b style="color:{c}">{ship}</b></div></div>')

def delivery(cfg, color):
    fee = "3,000원 (주문 수량마다 부과)" if cfg["ship"] else "무료배송"
    return (f'<div style="padding:60px 44px;background:#fff;color:#333;font-size:21px;line-height:1.85;text-align:left;word-break:keep-all;">'
            f'<h2 style="font-size:32px;margin:0 0 22px;border-left:9px solid {color};padding-left:16px;font-weight:800;">배송·교환·반품 안내</h2>'
            f'<p style="margin:0 0 12px;"><b>배송비</b> : {fee}</p>'
            '<p style="margin:0 0 12px;"><b>배송</b> : 결제 확인 후 순차적으로 발송되며, 택배사 사정에 따라 도착일이 달라질 수 있어요.</p>'
            '<p style="margin:0 0 12px;"><b>교환·반품</b> : 수령 후 7일 이내 신청할 수 있어요. 단순 변심의 경우 왕복 택배비 6,000원이 발생합니다.</p>'
            '<p style="margin:0 0 12px;">사용 흔적이 있거나 훼손된 경우, 개봉 후 위생상 재판매가 어려운 경우에는 교환·환불이 어려워요.</p>'
            '<p style="margin:0;">문의는 스토어 톡톡으로 남겨 주세요.</p></div>')

def build_detail(key, cfg, urls):
    f = FAM[cfg["fam"]]
    texts = PS_TEXT if cfg["fam"] == "폭싹" else TW_TEXT
    parts = [intro(key, cfg)]
    for i, u in enumerate(urls):
        parts.append(f'<img src="{u}" alt="{html.escape(f["model"])}" style="display:block;width:100%;height:auto;margin:0 auto;" />')
        if i in texts: parts.append(inline(texts[i], f["color"], f["bg"]))
    parts.append(delivery(cfg, f["color"]))
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">' + "".join(parts) + "</div>"

# ------------------------------------------------------------------ 페이로드
def payload(key, cfg, main_urls, detail):
    f = FAM[cfg["fam"]]
    single = cfg["ship"] > 0
    fee = ({"deliveryFeeType": "UNIT_QUANTITY_PAID", "baseFee": cfg["ship"], "deliveryFeePayType": "PREPAID", "repeatQuantity": 1}
           if single else {"deliveryFeeType": "FREE"})
    op = {
        "statusType": "SALE", "saleType": "NEW", "leafCategoryId": cfg["cat"], "name": cfg["name"], "detailContent": detail,
        "images": {"representativeImage": {"url": main_urls[0]}, "optionalImages": [{"url": u} for u in main_urls[1:9]]},
        "salePrice": cfg["price"], "stockQuantity": 999,
        "deliveryInfo": {"deliveryType": "DELIVERY", "deliveryAttributeType": "NORMAL", "deliveryCompany": STORE.get("delivery_company", "CJGLS"),
                         "deliveryBundleGroupUsable": False, "deliveryFee": fee,
                         "claimDeliveryInfo": {"returnDeliveryFee": 6000, "exchangeDeliveryFee": 6000}},
        "detailAttribute": {
            "afterServiceInfo": {"afterServiceTelephoneNumber": STORE["after_service_telephone"], "afterServiceGuideContent": STORE["after_service_guide"]},
            "originAreaInfo": f["origin"], "minorPurchasable": True, "taxType": "TAX",
            "naverShoppingSearchInfo": {"brandName": f["brand"], "manufacturerName": f["maker"], "modelName": f["model"]},
            "sellerCommentUsable": False,
            "productInfoProvidedNotice": {"productInfoProvidedNoticeType": "ETC", "etc": {
                "itemName": f["item"][:50], "modelName": f["model"][:50], "certificateDetails": f["cert"],
                "manufacturer": f["maker"], "customerServicePhoneNumber": STORE["after_service_telephone"]}},
            "certificationTargetExcludeContent": {"childCertifiedProductExclusionYn": True, "kcCertifiedProductExclusionYn": "TRUE", "greenCertifiedProductExclusionYn": True},
            "seoInfo": {"sellerTags": [{"text": t} for t in cfg["tags"]]},
        },
    }
    if cfg.get("opts"):
        op["detailAttribute"]["optionInfo"] = {
            "optionCombinationSortType": "CREATE", "optionCombinationGroupNames": {"optionGroupName1": cfg["optgroup"]},
            "optionCombinations": [{"optionName1": o, "stockQuantity": 999, "price": 0, "usable": True} for o in cfg["opts"]],
            "useStockManagement": True}
    return {"originProduct": op, "smartstoreChannelProduct": {"naverShoppingRegistration": True, "channelProductDisplayStatusType": "ON"}}

def post_with_retry(pl):
    for _ in range(8):
        r = requests.post(PROD_URL, headers={**auth_headers(), "Content-Type": "application/json"}, json=pl, timeout=120)
        m = re.search(r"등록불가인 단어\(([^)]+)\)", r.text) if r.status_code == 400 and "Restricted.sellerTags" in r.text else None
        if r.status_code == 429:
            time.sleep(8); continue
        if not m: return r
        bads = [b.strip() for b in m.group(1).split(",")]; print(f"    제한어 태그 제외: {bads}")
        tags = pl["originProduct"]["detailAttribute"]["seoInfo"]["sellerTags"]
        pl["originProduct"]["detailAttribute"]["seoInfo"]["sellerTags"] = [t for t in tags if not any(b in t["text"] for b in bads)]
    return r

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--only")
    a = ap.parse_args()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    cache = {}
    for key, cfg in LISTINGS.items():
        if a.only and a.only != key: continue
        if state.get(key, {}).get("productNo"):
            print(f"[=] {key} 이미 등록됨"); continue
        ck = (cfg["fam"], cfg.get("variant"))
        if a.dry:
            n = len(detail_slices(*ck)) if ck not in cache else len(cache[ck]); cache[ck] = cache.get(ck) or ["x"] * n
            dt = build_detail(key, cfg, ["https://example.invalid/%d.jpg" % i for i in range(n)])
            mains = main_images(key, cfg)
            print(f"[dry] {key}: 상품명 {len(cfg['name'])}자, 상세 {len(dt):,}자, 조각 {n}, 대표 {len(mains)}장, 태그 {len(cfg['tags'])}")
            continue
        if ck not in cache:
            sl = detail_slices(*ck)
            cache[ck] = upload([(f"{cfg['fam']}-{i:02d}.jpg", jpeg(im)) for i, im in enumerate(sl)])
            print(f"[+] {ck} 상세 {len(cache[ck])}조각 업로드")
        mains = upload(main_images(key, cfg))
        pl = payload(key, cfg, mains, build_detail(key, cfg, cache[ck]))
        r = post_with_retry(pl)
        if r.status_code != 200:
            print(f"[!] {key} 실패 {r.status_code}: {r.text[:900]}")
            state[key] = {"error": r.text[:900]}; STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
            continue
        d = r.json()
        state[key] = {"productNo": d.get("smartstoreChannelProductNo") or d.get("productNo"), "originProductNo": d.get("originProductNo"),
                      "name": cfg["name"], "price": cfg["price"], "at": datetime.now().isoformat()}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[+] {key} 등록 {state[key]['productNo']}"); time.sleep(1)

if __name__ == "__main__":
    main()
