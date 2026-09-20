"""헬스펫 9개 상품 스마트스토어 등록.

사용법:
  python3 register_healthpet.py --dry          # 페이로드만 만들고 저장 (API 등록 없음)
  python3 register_healthpet.py --only 힙앤조인트-단품   # 한 개만 등록
  python3 register_healthpet.py                # 남은 상품 전부 등록 (이미 등록된 것은 건너뜀)
"""
import argparse, html, io, json, re, sys, time
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image

HERE = Path(__file__).resolve().parent
SHOP = HERE.parent / "shoping-auto"
THUMB = HERE.parent / "0_헬스펫 반려동물 영양제3종 상세페이지" / "0_헬스펫 반려동물 영양제3종 상세페이지" / ".." / "섬네일_헬스펫"
THUMB = THUMB.resolve()
sys.path.insert(0, str(SHOP / "scripts"))
from naver_auth import API_BASE, auth_headers  # noqa: E402

STORE = json.loads((SHOP / "config" / "store.json").read_text(encoding="utf-8"))
STATE = HERE / "등록결과.json"
IMAGE_UPLOAD_URL = f"{API_BASE}/v1/product-images/upload"
PRODUCT_URL = f"{API_BASE}/v2/products"

# build.py 에서 상세 문구·조각 구성을 가져온다(빌드는 실행하지 않는다).
_src = (Path(__file__).resolve().parent.parent / "헬스펫_블로그형_상세페이지" / "build_source.py")
_ns: dict = {}
exec(_src.read_text(encoding="utf-8").split("def build(")[0], _ns)
PRODUCTS = _ns["products"]

DOG_SUP, DOG_PROBIO, CAT_SUP, CAT_PROBIO = "50006655", "50006656", "50006705", "50006706"

MODEL = {
    "힙앤조인트": dict(brand="헬스펫", maker="선바이오연구소(주)", model="헬스펫 관절케어 힙앤조인트 미세과립형",
                   item="헬스펫 관절케어 힙앤조인트 미세과립형 (애완용 배합사료)", thumbs=["힙앤조인트-섬네일%d.jpg" % i for i in (1, 2, 3, 4, 5)],
                   spec="60g", color="#F08A3C", lead="관절 영양"),
    "프로바이오틱스": dict(brand="헬스펫", maker="선바이오연구소(주)", model="헬스펫 장케어 프로바이오틱스 미세과립형",
                     item="헬스펫 장케어 프로바이오틱스 미세과립형 (애완용 배합사료)", thumbs=["프로바이오틱스-섬네일%d.jpg" % i for i in (1, 2, 3, 4, 5)],
                     spec="60g", color="#E9B400", lead="장 건강"),
    "오메가3": dict(brand="헬스펫", maker="선바이오연구소(주)", model="헬스펫 데일리케어 오메가3 오일형",
                 item="헬스펫 데일리케어 오메가3 오일형 (애완용 배합사료)", thumbs=["오메가3-섬네일%d.jpg" % i for i in (1, 2, 3, 4)],
                 spec="40mL", color="#E8833A", lead="오메가3"),
}

# (제품, 구분) -> 상품명, 카테고리, 판매가, 배송, 옵션명, 대표이미지 인덱스(1부터), 태그
LISTINGS = {
    ("힙앤조인트", "단품"): dict(
        name="헬스펫 힙앤조인트 강아지 글루코사민 MSM 관절 영양제 분말 60g", cat=DOG_SUP, price=24900, main=1,
        tags=["강아지글루코사민", "강아지MSM", "강아지관절", "강아지초록입홍합", "강아지관절영양제추천", "애견관절영양제", "강아지영양제", "힙앤조인트", "헬스펫", "관절영양제"]),
    ("힙앤조인트", "3개"): dict(
        name="노령견 관절 영양제 초록입홍합 보스웰리아 힙앤조인트 60g 3개 세트 무료배송", cat=DOG_SUP, price=79900, main=3, option="3개 세트 무료배송",
        tags=["노령견영양제", "노견영양제", "반려견관절영양제", "강아지관절영양제", "강아지근육영양제", "강아지뼈영양제", "강아지영양제세트", "힙앤조인트3개", "관절영양제세트", "헬스펫관절"]),
    ("힙앤조인트", "5개"): dict(
        name="대형견 관절 영양제 반려견 관절 헬스펫 힙앤조인트 60g 5개 세트 무료배송", cat=DOG_SUP, price=129900, main=4, option="5개 세트 무료배송",
        tags=["대형견관절영양제", "대형견영양제", "반려견영양제", "애견영양제", "강아지영양제추천", "관절영양제대용량", "힙앤조인트5개", "강아지영양제5개", "반려견관절", "헬스펫영양제"]),
    ("프로바이오틱스", "단품"): dict(
        name="강아지 프로바이오틱스 헬스펫 장케어 5종 복합유산균 프리바이오틱스 60g", cat=DOG_PROBIO, price=24900, main=1,
        tags=["강아지프로바이오틱스", "강아지장영양제", "강아지장유산균", "유산균강아지", "강아지장건강", "강아지장건강영양제", "강아지유산균추천", "반려동물유산균", "장케어", "헬스펫"]),
    ("프로바이오틱스", "3개"): dict(
        name="고양이 유산균 프로바이오틱스 헬스펫 장케어 분말 60g 3개 세트 무료배송", cat=CAT_PROBIO, price=79900, main=3, option="3개 세트 무료배송",
        tags=["고양이유산균", "고양이프로바이오틱스", "고양이유산균추천", "고양이장영양제", "고양이영양제", "고양이영양제추천", "고양이유산균세트", "펫유산균", "장케어3개", "헬스펫유산균"]),
    ("프로바이오틱스", "5개"): dict(
        name="애견 유산균 반려견 노견 유산균 헬스펫 장케어 분말 60g 5개 세트 무료배송", cat=DOG_PROBIO, price=129900, main=4, option="5개 세트 무료배송",
        tags=["애견유산균", "반려견유산균", "노견유산균", "대형견유산균", "강아지유산균대용량", "강아지유산균5개", "장케어5개", "펫유산균세트", "강아지영양제세트", "헬스펫프로바이오틱스"]),
    ("오메가3", "단품"): dict(
        name="애견 오메가3 헬스펫 데일리케어 참치 오일 영양제 펌프형 40ml", cat=DOG_SUP, price=24900, main=1,
        tags=["애견오메가3", "강아지오메가", "강아지오일", "강아지털영양제", "강아지오메가3추천", "반려견오일영양제", "펌핑오메가3", "강아지영양제", "데일리케어", "헬스펫"]),
    ("오메가3", "3개"): dict(
        name="고양이 오메가3 오일 헬스펫 데일리케어 40ml 3개 세트 무료배송", cat=CAT_SUP, price=79900, main=2, option="3개 세트 무료배송",
        tags=["고양이오메가3", "고양이오메가3추천", "고양이영양제", "고양이영양제추천", "고양이털영양제", "고양이오일", "고양이오메가3세트", "펫오메가3", "오메가3세트", "헬스펫오메가3"]),
    ("오메가3", "5개"): dict(
        name="반려견 오메가3 노견 오메가3 헬스펫 데일리케어 40ml 5개 세트 무료배송", cat=DOG_SUP, price=129900, main=4, option="5개 세트 무료배송",
        tags=["반려견오메가3", "노견오메가3", "노령견오메가3", "반려동물오메가3", "강아지영양제추천", "오메가3대용량", "강아지오메가35개", "오메가35개세트", "강아지영양제세트", "헬스펫영양제"]),
}


def slug(p, k):
    return f"{p}-{k}"


# ---------------------------------------------------------------- 이미지
def jpeg_bytes(path: Path) -> bytes:
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92, optimize=True)  # 재인코딩으로 EXIF 제거
    return buf.getvalue()


def upload(files: list[tuple[str, bytes]]) -> list[str]:
    urls = []
    for i in range(0, len(files), 5):
        chunk = files[i:i + 5]
        payload = [("imageFiles", (name, data, "image/jpeg")) for name, data in chunk]
        r = requests.post(IMAGE_UPLOAD_URL, headers=auth_headers(), files=payload, timeout=180)
        if r.status_code != 200:
            raise RuntimeError(f"이미지 업로드 실패 {r.status_code}: {r.text[:400]}")
        got = [x["url"] for x in r.json().get("images", [])]
        if len(got) != len(chunk):
            raise RuntimeError(f"업로드 개수 불일치: {len(got)} != {len(chunk)}")
        urls += got
        time.sleep(0.5)
    return urls


# ---------------------------------------------------------------- 상세 HTML
def inline(html_txt: str, color: str, bg: str) -> str:
    s = html_txt
    s = s.replace('<div class="t box">', f'<div style="padding:56px 44px;color:#333;font-size:22px;line-height:1.8;background:#fff;border:3px dashed {color};margin:0;text-align:left;word-break:keep-all;">')
    s = s.replace('<div class="t">', f'<div style="padding:60px 44px;color:#333;font-size:22px;line-height:1.8;background:{bg};margin:0;text-align:left;word-break:keep-all;">')
    s = s.replace("<h2>", f'<h2 style="font-size:32px;line-height:1.45;margin:0 0 22px;color:#222;border-left:9px solid {color};padding-left:16px;font-weight:800;">')
    s = s.replace("<p>", '<p style="margin:0 0 16px;font-size:22px;line-height:1.8;">')
    s = s.replace("<b>", f'<b style="background:linear-gradient(transparent 60%,{color}55 60%);font-weight:800;">')
    s = s.replace("<small>", '<small style="font-size:17px;color:#777;">')
    return s


def intro_block(product: str, kind: str, cfg: dict, m: dict) -> str:
    c = m["color"]
    spec = m["spec"]
    if kind == "단품":
        label, ship = f"{spec} × 1개", "배송비 3,000원"
        note = "먼저 1개로 우리 아이 반응을 확인해 보세요."
    else:
        n = 3 if kind == "3개" else 5
        label, ship = f"{spec} × {n}개 세트", "<b style=\"color:%s\">무료배송</b>" % c
        note = f"{n}개를 한 번에 받으면 배송비 없이 넉넉하게 급여할 수 있어요."
    title = html.escape(m["model"])
    return (
        f'<div style="padding:70px 30px 50px;text-align:center;background:#fff;">'
        f'<div style="font-size:24px;font-weight:700;color:{c};">HEALTH PET</div>'
        f'<div style="font-size:40px;font-weight:800;line-height:1.4;margin:14px 0 18px;color:#111;word-break:keep-all;">{title}</div>'
        f'<div style="font-size:30px;font-weight:700;color:#222;margin-bottom:10px;">{label}</div>'
        f'<div style="font-size:26px;color:#444;margin-bottom:16px;">{ship}</div>'
        f'<div style="font-size:23px;color:#666;line-height:1.7;word-break:keep-all;">{note}</div></div>'
    )


def delivery_block(kind: str, color: str) -> str:
    fee = "3,000원 (주문 수량마다 부과)" if kind == "단품" else "무료배송"
    return (
        f'<div style="padding:60px 44px;background:#fff;color:#333;font-size:21px;line-height:1.85;text-align:left;word-break:keep-all;">'
        f'<h2 style="font-size:32px;margin:0 0 22px;border-left:9px solid {color};padding-left:16px;font-weight:800;">배송·교환·반품 안내</h2>'
        f'<p style="margin:0 0 12px;"><b>배송비</b> : {fee}</p>'
        '<p style="margin:0 0 12px;"><b>배송</b> : 결제 확인 후 순차적으로 발송되며, 택배사 사정에 따라 도착일이 달라질 수 있어요.</p>'
        '<p style="margin:0 0 12px;"><b>교환·반품</b> : 제품 수령 후 7일 이내 신청할 수 있어요. 단순 변심의 경우 왕복 택배비 6,000원이 발생합니다.</p>'
        '<p style="margin:0 0 12px;">제품에 사용 흔적이 있거나 훼손된 경우, 개봉 후 변질된 경우에는 교환·환불이 어려워요. 제품 자체의 불량은 소비자분쟁해결기준에 따릅니다.</p>'
        '<p style="margin:0;">문의는 스토어 톡톡으로 남겨 주세요.</p></div>'
    )


def build_detail(product: str, kind: str, urls: list[str]) -> str:
    m = MODEL[product]
    d = PRODUCTS[product]
    parts = [intro_block(product, kind, LISTINGS[(product, kind)], m)]
    it = iter(urls)
    imgs = [u for u in urls]
    idx = 0
    body = []
    for item in d["items"]:
        if item[0] == "img":
            body.append(f'<img src="{imgs[idx]}" alt="{html.escape(m["model"])}" style="display:block;width:100%;height:auto;margin:0 auto;" />')
            idx += 1
        elif item[0] == "txt":
            body.append(inline(item[1], d["color"], d["bg"]))
    # 주의사항 이미지 뒤, 원재료 이미지 앞에 우리 배송안내를 넣는다.
    parts += body[:-1] + [delivery_block(kind, d["color"])] + body[-1:]
    return '<div style="max-width:860px;margin:0 auto;font-family:\'Apple SD Gothic Neo\',\'Malgun Gothic\',Arial,sans-serif;">' + "".join(parts) + "</div>"


# ---------------------------------------------------------------- 페이로드
def build_payload(product: str, kind: str, main_urls: list[str], detail_html: str) -> dict:
    cfg = LISTINGS[(product, kind)]
    m = MODEL[product]
    single = kind == "단품"
    delivery_fee = (
        {"deliveryFeeType": "UNIT_QUANTITY_PAID", "baseFee": 3000, "deliveryFeePayType": "PREPAID", "repeatQuantity": 1}
        if single else {"deliveryFeeType": "FREE"}
    )
    op = {
        "statusType": "SALE", "saleType": "NEW", "leafCategoryId": cfg["cat"], "name": cfg["name"],
        "detailContent": detail_html,
        "images": {"representativeImage": {"url": main_urls[0]}, "optionalImages": [{"url": u} for u in main_urls[1:9]]},
        "salePrice": cfg["price"], "stockQuantity": 999,
        "deliveryInfo": {
            "deliveryType": "DELIVERY", "deliveryAttributeType": "NORMAL", "deliveryCompany": STORE.get("delivery_company", "CJGLS"),
            "deliveryBundleGroupUsable": False, "deliveryFee": delivery_fee,
            "claimDeliveryInfo": {"returnDeliveryFee": 6000, "exchangeDeliveryFee": 6000},
        },
        "detailAttribute": {
            "afterServiceInfo": {"afterServiceTelephoneNumber": STORE["after_service_telephone"], "afterServiceGuideContent": STORE["after_service_guide"]},
            "originAreaInfo": {"originAreaCode": "0001", "content": "국내산(강원특별자치도 원주)", "plural": False},
            "minorPurchasable": True, "taxType": "TAX",
            "naverShoppingSearchInfo": {"brandName": m["brand"], "manufacturerName": m["maker"], "modelName": m["model"]},
            "sellerCommentUsable": False,
            "productInfoProvidedNotice": {
                "productInfoProvidedNoticeType": "ETC",
                "etc": {
                    "itemName": m["item"][:50], "modelName": m["model"][:50],
                    "certificateDetails": "애완동물용 배합사료(성분등록 제 %s 호), HACCP 적용 사료공장 제조" % {"힙앤조인트": "881E60050", "프로바이오틱스": "881E60064", "오메가3": "881E60081"}[product],
                    "manufacturer": m["maker"],
                    "customerServicePhoneNumber": STORE["after_service_telephone"],
                },
            },
            "certificationTargetExcludeContent": {"childCertifiedProductExclusionYn": True, "kcCertifiedProductExclusionYn": "TRUE", "greenCertifiedProductExclusionYn": True},
            "seoInfo": {"sellerTags": [{"text": t} for t in cfg["tags"]]},
        },
    }
    if not single:
        op["detailAttribute"]["optionInfo"] = {
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {"optionGroupName1": "구성"},
            "optionCombinations": [{"optionName1": cfg["option"], "stockQuantity": 999, "price": 0, "usable": True}],
            "useStockManagement": True,
        }
    return {"originProduct": op, "smartstoreChannelProduct": {"naverShoppingRegistration": True, "channelProductDisplayStatusType": "ON"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    detail_cache: dict = {}
    for (product, kind), cfg in LISTINGS.items():
        key = slug(product, kind)
        if args.only and args.only != key:
            continue
        if key in state and state[key].get("productNo"):
            print(f"[=] {key} 이미 등록됨 ({state[key]['productNo']})")
            continue
        m = MODEL[product]
        if args.dry:
            urls_detail = [f"https://example.invalid/{i}.jpg" for i in range(len(list((HERE / product).glob('*.jpg'))))]
            main_urls = ["https://example.invalid/m.jpg"]
        else:
            if product not in detail_cache:
                files = [(p.name, p.read_bytes()) for p in sorted((HERE / product).glob("*.jpg"))]
                detail_cache[product] = upload(files)
            urls_detail = detail_cache[product]
            order = [cfg["main"]] + [i for i in range(1, len(m["thumbs"]) + 1) if i != cfg["main"]]
            main_files = [(f"{key}-{n}.jpg", jpeg_bytes(THUMB / m["thumbs"][i - 1])) for n, i in enumerate(order[:5], 1)]
            main_urls = upload(main_files)
        detail = build_detail(product, kind, urls_detail)
        payload = build_payload(product, kind, main_urls, detail)
        (HERE / "payload_preview").mkdir(exist_ok=True)
        (HERE / "payload_preview" / f"{key}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        if args.dry:
            print(f"[dry] {key}: 상품명 {len(cfg['name'])}자, 상세 {len(detail):,}자, 태그 {len(cfg['tags'])}개")
            continue
        for _ in range(6):
            r = requests.post(PRODUCT_URL, headers={**auth_headers(), "Content-Type": "application/json"}, json=payload, timeout=90)
            mm = re.search(r"등록불가인 단어\(([^)]+)\)", r.text) if r.status_code == 400 and "Restricted.sellerTags" in r.text else None
            if not mm:
                break
            bad = mm.group(1)  # 제한어 응답을 받은 태그는 우회하지 않고 제외한다
            print(f"    제한어 태그 제외: {bad}")
            tags = payload["originProduct"]["detailAttribute"]["seoInfo"]["sellerTags"]
            payload["originProduct"]["detailAttribute"]["seoInfo"]["sellerTags"] = [t for t in tags if bad not in t["text"]]
        if r.status_code != 200:
            print(f"[!] {key} 등록 실패 {r.status_code}: {r.text[:1500]}")
            state[key] = {"error": r.text[:1500], "at": datetime.now().isoformat()}
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
            if args.only:
                sys.exit(1)
            continue
        data = r.json()
        state[key] = {"productNo": data.get("smartstoreChannelProductNo") or data.get("productNo"), "originProductNo": data.get("originProductNo"),
                      "name": cfg["name"], "price": cfg["price"], "at": datetime.now().isoformat()}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[+] {key} 등록 완료 {state[key]['productNo']}")
        time.sleep(1)


if __name__ == "__main__":
    main()
