"""부산코코상회 공개 베스트 상품의 개별 페이지 자료 제공 여부를 점검한다.

판매량·실시간 재고는 공개 페이지에서 확정할 수 없으므로 추정하지 않는다.
상세 이미지와 고시/라벨 정보가 있는 상품만 다음 등록 검증 단계로 넘긴다.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "research" / "cocomart-bests.json"
DEFAULT_OUTPUT = ROOT / "research" / "cocomart-best-product-pages.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"
    )
}


def detail_assets(page: str, source_url: str) -> list[str]:
    start = page.find('id="prdDetail"')
    end = page.find('id="tab02"', start)
    detail = page[start : end if end >= 0 else len(page)] if start >= 0 else ""
    assets = re.findall(r'(?:ec-data-src|src)="([^"]+)"', detail)
    urls = []
    for asset in assets:
        url = urljoin(source_url, asset)
        if url not in urls and not url.endswith("detail_img_top_1.png"):
            urls.append(url)
    return urls


def inspect_product(product: dict) -> dict:
    result = dict(product)
    try:
        response = requests.get(product["source_url"], headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        result.update(
            {
                "status": "page_fetch_failed",
                "page_verification": {"error": str(exc)},
            }
        )
        return result

    page = response.text
    assets = detail_assets(page, product["source_url"])
    # Cafe24 템플릿의 숨김 SOLD OUT 문구는 재고 신호가 아니므로 기록만 하고 판정에 쓰지 않는다.
    result.update(
        {
            "status": "needs_label_and_stock_verification",
            "page_verification": {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "http_status": response.status_code,
                "detail_image_count": len(assets),
                "detail_image_urls": assets,
                "purchase_ui_present": "product_submit(2" in page,
                "sales_volume_disclosed": False,
                "stock_note": "공개 페이지의 숨김 SOLD OUT 템플릿은 재고 근거로 사용하지 않음",
                "next_required": [
                    "실제 재고 또는 주문 가능 상태 확인",
                    "라벨에서 고시·원산지·보관법 확인",
                    "가격 계산과 카테고리 검증",
                ],
            },
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="부산코코상회 베스트 상품 페이지 검증")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    products = []
    for product in source["products"]:
        products.append(inspect_product(product))
        sleep(0.2)

    payload = {
        "source": source["source"],
        "source_bests_checked_at": source["checked_at"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "products": products,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pages_ok = sum(p["status"] != "page_fetch_failed" for p in products)
    print(f"[+] 상품 페이지 자료 확인: {pages_ok}/{len(products)}개")


if __name__ == "__main__":
    main()
