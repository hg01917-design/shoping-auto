"""황동판 누룽지(450g/1kg), 12곡 미숫가루 등록.  python3 register_food.py [--dry] [--only KEY]"""
import argparse, glob, html, io, json, os, re, sys, time
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import register_new as R  # noqa: E402
from slicer import load_stack, W  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
STATE = HERE / "등록결과_식품.json"
NR = R.ROOT / "황동판누룽지"
NR450 = glob.glob(str(NR / "*450g"))[0]
NR1K = glob.glob(str(NR / "*1kg*"))[0]
MS = NR / "12곡미숫가루"
DETAIL_NR = glob.glob(os.path.join(NR1K, "KakaoTalk_20260508_180528679.jpg"))[0]   # 라벨에 150g~1kg 표기
DETAIL_MS = glob.glob(str(MS / "*상세페이지-수정본.jpg"))[0]

FOODFAM = {
    "누룽지": dict(color="#B8862F", bg="#FBF4E4", brand="황동판", maker="미성푸드", model="황동판에 구워 구수한 누룽지",
                 item="황동판에 구워 구수한 누룽지", foodtype="곡류가공품", loc="경기도 광주시 곤지암읍 장심길 108",
                 origin=dict(originAreaCode="00", content="국산", plural=False),
                 ingredients="쌀(백미) 100% (국내산)", caution="치아가 안 좋으신 분들은 끓이거나 조리하여 드십시오. 부정·불량식품 신고는 국번없이 1399",
                 phone="031-765-0120", cat="50012400"),
    "미숫가루": dict(color="#A66B2F", bg="#FBF3E8", brand="미성푸드", maker="성진식품", model="12곡 미숫가루",
                  item="12곡 미숫가루", foodtype="곡류가공품", loc="경기도 광주시 도척면 마도로 244-71",
                  origin=dict(originAreaCode="03", content="원재료명 참조 (보리 국내산, 밀·백태 미국산 등)", plural=True),
                  ingredients="보리(국내산), 밀(미국산), 백태(미국산), 찐쌀, 옥수수, 찐찹쌀, 찐현미, 검정콩, 수수, 율무, 차조, 흑미",
                  caution="메밀, 우유 혼입 가능성 있음. 부정·불량식품 신고는 국번없이 1399", phone="080-761-0623", cat="50017880"),
}

L = {
    "누룽지450-단품": dict(fam="누룽지", size="450g", n=1, price=6900, ship=3000, detail="nr", img="450",
        name="황동판 현미 아닌 백미 누룽지 450g 국산쌀 100% 구수한 누룽지", opts=None,
        tags=["누룽지", "황동판누룽지", "가마솥누룽지", "국산누룽지", "누룽지간식", "쌀누룽지", "수제누룽지", "누룽지끓이는법", "곡류가공품", "미성푸드"]),
    "누룽지450-3개": dict(fam="누룽지", size="450g", n=3, price=24900, ship=0, detail="nr", img="450",
        name="황동판 구운 누룽지 450g 3개 세트 국산쌀 무료배송 누룽지탕", opts=None,
        tags=["누룽지탕", "누룽지세트", "간편식", "아침대용", "국산쌀누룽지", "누룽지선물", "누룽지3개", "가마솥누룽지", "황동판", "구수한누룽지"]),
    "누룽지450-5개": dict(fam="누룽지", size="450g", n=5, price=37900, ship=0, detail="nr", img="450",
        name="황동판에 구운 누룽지 450g 5개 대용량 세트 국산쌀 무료배송", opts=None,
        tags=["누룽지5개", "누룽지대용량", "쌀누룽지", "누룽지끓이는법", "누룽지스낵", "누룽지간식", "국산누룽지", "누룽지만들기", "미성푸드누룽지", "누룽지선물세트"]),
    "누룽지1kg-단품": dict(fam="누룽지", size="1kg", n=1, price=10900, ship=3000, detail="nr", img="1k",
        name="황동판에 구운 누룽지 1kg 국산쌀 백미 누룽지 대용량", opts=None,
        tags=["누룽지1kg", "누룽지대용량", "국산쌀누룽지", "가마솥누룽지", "누룽지탕", "황동판누룽지", "수제누룽지", "누룽지간식", "쌀누룽지", "구수한누룽지"]),
    "누룽지1kg-3개": dict(fam="누룽지", size="1kg", n=3, price=36900, ship=0, detail="nr", img="1k",
        name="황동판 누룽지 1kg 3개 세트 국산쌀 구운 누룽지 무료배송", opts=None,
        tags=["누룽지3kg", "누룽지대용량세트", "누룽지세트", "누룽지선물", "누룽지1kg3개", "국산누룽지", "간편식", "누룽지탕", "황동판", "누룽지스낵"]),
    "누룽지1kg-5개": dict(fam="누룽지", size="1kg", n=5, price=59900, ship=0, detail="nr", img="1k",
        name="누룽지 1kg 5개 세트 황동판에 구운 국산쌀 누룽지 대용량 무료배송", opts=None,
        tags=["누룽지5kg", "누룽지대용량", "누룽지업소용", "누룽지5개", "국산쌀누룽지", "누룽지선물세트", "누룽지간식", "가마솥누룽지", "황동판누룽지", "누룽지끓이는법"]),
    "미숫가루-단품": dict(fam="미숫가루", size="1kg", n=1, price=9900, ship=3000, detail="ms", img="ms",
        name="12곡 미숫가루 1kg 미성푸드 곡물 12가지 미숫가루 아침대용", opts=None,
        tags=["12곡미숫가루", "미숫가루", "미숫가루라떼", "곡물미숫가루", "미숫가루우유", "옛날미숫가루", "검은콩미숫가루", "미숫가루추천", "국산미숫가루", "간편식"]),
    "미숫가루-3개": dict(fam="미숫가루", size="1kg", n=3, price=29900, ship=0, detail="ms", img="ms",
        name="12곡 미숫가루 1kg 3개 세트 곡물 12가지 미숫가루 무료배송", opts=None,
        tags=["미숫가루", "미숫가루3개", "미숫가루세트", "12곡", "미숫가루타는법", "미숫가루라떼", "곡물가루", "미숫가루우유", "아침대용", "미숫가루추천"]),
    "미숫가루-5개": dict(fam="미숫가루", size="1kg", n=5, price=51900, ship=0, detail="ms", img="ms",
        name="12곡 미숫가루 1kg 5개 대용량 세트 곡물 미숫가루 무료배송", opts=None,
        tags=["미숫가루대용량", "미숫가루5개", "12곡미숫가루", "곡물미숫가루", "선식", "미숫가루재료", "국산곡물", "간식대용", "미숫가루추천", "미숫가루우유"]),
}

def T(h, *ps, small=None):
    s = '<div class="t">'
    if h: s += f"<h2>{h}</h2>"
    for p in ps: s += f"<p>{p}</p>"
    if small: s += f"<small>{small}</small>"
    return s + "</div>"

TEXT = {
    "nr": {1: T("토독, 밥솥 바닥의 그 소리", "어릴 적 엄마가 밥을 짓고 나면 바닥에 남던 <b>구수한 누룽지</b>. 황동판에 구워 그 맛을 그대로 담았어요."),
           6: T("쌀만 넣고, 국내산으로", "원재료는 <b>쌀(백미) 100%(국내산)</b>이에요. 다른 재료를 섞지 않고 쌀 본연의 고소함에 집중했습니다."),
           4: T("이렇게 드셔 보세요", "<b>따뜻한 물을 부어 누룽지탕으로</b>, 우유나 두유에 말아서, 기름에 튀겨 바삭한 간식으로, 국이나 전골에 넣어 마무리 밥으로도 좋아요."),
           9: T("보관은 실온에서", "직사광선과 습기 찬 곳을 피해 <b>실온</b>에서 보관해 주세요. 치아가 안 좋으신 분은 끓이거나 조리해서 드세요.", small="※ 식품유형 곡류가공품 · 제조원 미성푸드(경기도 광주시)")},
    "ms": {1: T("한 잔이면 든든한 아침", "12가지 곡물을 볶아 곱게 갈아 만든 <b>12곡 미숫가루</b>. 물이나 우유에 타서 <b>간단하게 한 끼 대용</b>으로 드셔 보세요."),
           7: T("타는 방법도 간단해요", "미숫가루 3스푼을 잔에 넣고 <b>차가운 물이나 우유, 두유, 얼음</b>을 넣어 저어 주세요. 꿀이나 오트밀을 더해 드시는 분도 많아요."),
           13: T("원재료를 꼼꼼히 확인하세요", "보리(국내산), 밀·백태(미국산), 찐쌀, 옥수수, 찐찹쌀, 찐현미, 검정콩, 수수, 율무, 차조, 흑미가 들어 있어요.", small="※ 메밀, 우유 혼입 가능성이 있어요. 알레르기가 있으신 분은 주의해 주세요.")},
}

def slices(kind):
    f = DETAIL_NR if kind == "nr" else DETAIL_MS
    st, _ = load_stack([f]); a = np.asarray(st); H = a.shape[0]
    std = a.reshape(H, -1).astype(np.float32).std(axis=1)
    def blank(y, r=600):
        lo = max(1, y - r); hi = min(H - 1, y + r)
        idx = [i for i in range(lo, hi) if std[i] < 5]
        return min(idx, key=lambda i: abs(i - y)) if idx else lo + int(np.argmin(std[lo:hi]))
    cuts = [0]; y = 0
    while H - y > 2600:
        ny = blank(y + 1900)
        if ny <= y + 900: ny = blank(y + 2300)
        y = ny; cuts.append(y)
    cuts.append(H)
    return [st.crop((0, cuts[i], W, cuts[i + 1])) for i in range(len(cuts) - 1)]

def main_imgs(key, cfg):
    if cfg["img"] == "450":
        ps = sorted(glob.glob(NR450 + "/*.png"))
    elif cfg["img"] == "1k":
        ps = [glob.glob(NR1K + "/KakaoTalk_20260508_175124991.jpg")[0]]
    else:
        ps = [glob.glob(str(MS / f"12곡미숫가루 대표이미지 ({i}).jpg"))[0] for i in (2, 4, 14, 23, 1)]
    out = []
    for i, p in enumerate(ps[:5], 1):
        im = Image.open(p).convert("RGB"); m = max(im.size)
        if m < 800: im = im.resize((int(im.width * 800 / m), int(im.height * 800 / m)), Image.LANCZOS)
        s = max(im.size); c = Image.new("RGB", (s, s), "white"); c.paste(im, ((s - im.width) // 2, (s - im.height) // 2))
        out.append((f"{key}-{i}.jpg", R.jpeg(c, 90)))
    return out

def intro(key, cfg):
    f = FOODFAM[cfg["fam"]]; c = f["color"]
    label = f'{cfg["size"]} × {cfg["n"]}개' if cfg["n"] > 1 else f'{cfg["size"]}'
    ship = "무료배송" if cfg["ship"] == 0 else "배송비 3,000원"
    return (f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;">'
            f'<div style="font-size:22px;font-weight:700;color:{c};">{html.escape(f["brand"])}</div>'
            f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0;color:#111;word-break:keep-all;">{html.escape(f["model"])}</div>'
            f'<div style="font-size:32px;font-weight:800;color:#222;">{label}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:10px;">{cfg["price"]:,}원 · <b style="color:{c}">{ship}</b></div></div>')

def detail(key, cfg, urls):
    f = FOODFAM[cfg["fam"]]; texts = TEXT[cfg["detail"]]
    parts = [intro(key, cfg)]
    for i, u in enumerate(urls):
        parts.append(f'<img src="{u}" alt="{html.escape(f["model"])}" style="display:block;width:100%;height:auto;margin:0 auto;" />')
        if i in texts: parts.append(R.inline(texts[i], f["color"], f["bg"]))
    parts.append(R.delivery(cfg, f["color"]))
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">' + "".join(parts) + "</div>"

def payload(key, cfg, mains, dt):
    f = FOODFAM[cfg["fam"]]
    fee = ({"deliveryFeeType": "UNIT_QUANTITY_PAID", "baseFee": cfg["ship"], "deliveryFeePayType": "PREPAID", "repeatQuantity": 1}
           if cfg["ship"] else {"deliveryFeeType": "FREE"})
    weight = f'{cfg["size"]} × {cfg["n"]}개'
    op = {
        "statusType": "SALE", "saleType": "NEW", "leafCategoryId": f["cat"], "name": cfg["name"], "detailContent": dt,
        "images": {"representativeImage": {"url": mains[0]}, "optionalImages": [{"url": u} for u in mains[1:9]]},
        "salePrice": cfg["price"], "stockQuantity": 999,
        "deliveryInfo": {"deliveryType": "DELIVERY", "deliveryAttributeType": "NORMAL", "deliveryCompany": R.STORE.get("delivery_company", "CJGLS"),
                         "deliveryBundleGroupUsable": False, "deliveryFee": fee,
                         "claimDeliveryInfo": {"returnDeliveryFee": 6000, "exchangeDeliveryFee": 6000}},
        "detailAttribute": {
            "afterServiceInfo": {"afterServiceTelephoneNumber": R.STORE["after_service_telephone"], "afterServiceGuideContent": R.STORE["after_service_guide"]},
            "originAreaInfo": f["origin"], "minorPurchasable": True, "taxType": "TAX",
            "naverShoppingSearchInfo": {"brandName": f["brand"], "manufacturerName": f["maker"], "modelName": f["model"]},
            "sellerCommentUsable": False,
            "productInfoProvidedNotice": {"productInfoProvidedNoticeType": "GENERAL_FOOD", "generalFood": {
                "productName": f["item"], "foodType": f["foodtype"], "producer": f'{f["maker"]}', "location": f["loc"],
                "packDateText": "제품 포장에 별도 표시", "consumptionDateText": "제품 포장에 별도 표시일까지 (제조일로부터 표시기간 참조)",
                "weight": weight, "amount": weight, "ingredients": f["ingredients"], "nutritionFacts": "제품 포장 및 상세 이미지 참조",
                "geneticallyModified": False, "consumerSafetyCaution": f["caution"], "importDeclarationCheck": False,
                "customerServicePhoneNumber": f["phone"]}},
            "certificationTargetExcludeContent": {"childCertifiedProductExclusionYn": True, "kcCertifiedProductExclusionYn": "TRUE", "greenCertifiedProductExclusionYn": True},
            "seoInfo": {"sellerTags": [{"text": t} for t in cfg["tags"]]},
        },
    }
    return {"originProduct": op, "smartstoreChannelProduct": {"naverShoppingRegistration": True, "channelProductDisplayStatusType": "ON"}}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--only")
    a = ap.parse_args()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    cache = {}
    for key, cfg in L.items():
        if a.only and a.only != key: continue
        if state.get(key, {}).get("productNo"): print(f"[=] {key} 이미 등록됨"); continue
        if a.dry:
            n = len(slices(cfg["detail"])) if cfg["detail"] not in cache else cache[cfg["detail"]]; cache[cfg["detail"]] = n
            dt = detail(key, cfg, ["https://example.invalid/%d.jpg" % i for i in range(n)])
            print(f"[dry] {key}: 이름 {len(cfg['name'])}자 조각 {n} 대표 {len(main_imgs(key, cfg))}장 태그 {len(cfg['tags'])} 상세 {len(dt):,}")
            continue
        if cfg["detail"] not in cache:
            sl = slices(cfg["detail"])
            cache[cfg["detail"]] = R.upload([(f"{cfg['detail']}-{i:02d}.jpg", R.jpeg(im)) for i, im in enumerate(sl)])
            print(f"[+] {cfg['detail']} 상세 {len(cache[cfg['detail']])}조각 업로드", flush=True)
        mains = R.upload(main_imgs(key, cfg))
        pl = payload(key, cfg, mains, detail(key, cfg, cache[cfg["detail"]]))
        r = R.post_with_retry(pl)
        if r.status_code != 200:
            print(f"[!] {key} 실패 {r.status_code}: {r.text[:800]}", flush=True)
            state[key] = {"error": r.text[:800]}; STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8"); continue
        d = r.json()
        state[key] = {"productNo": d.get("smartstoreChannelProductNo") or d.get("productNo"), "originProductNo": d.get("originProductNo"), "name": cfg["name"], "price": cfg["price"], "at": datetime.now().isoformat()}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[+] {key} 등록 {state[key]['productNo']}", flush=True); time.sleep(1)

if __name__ == "__main__":
    main()
