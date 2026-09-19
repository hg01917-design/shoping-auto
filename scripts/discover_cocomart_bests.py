"""부산코코상회 홈페이지의 공개 '판매 베스트 상품' 진열을 조사한다.

사이트가 판매량을 공개하지 않으므로, 이 스크립트의 rank는 홈페이지 진열 순서일 뿐
실제 판매량이 아니다. 등록 전에는 각 상품의 품절 상태와 라벨 정보를 별도로 검증한다.

사용법:
    python3 scripts/discover_cocomart_bests.py
    python3 scripts/discover_cocomart_bests.py --output research/cocomart-bests.json
"""

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parent.parent
HOME_URL = "https://cocomart.co.kr/"
SECTION_MARKER = "xans-product-listmain-14"
SECTION_TITLE = "코스트코 인기제품 판매 베스트 상품"


def text_without_tags(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<.*?>", "", value)).split())


def discover() -> list[dict]:
    response = requests.get(
        HOME_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"
            )
        },
        timeout=30,
    )
    response.raise_for_status()
    page = response.text
    start = page.find(SECTION_MARKER)
    if start < 0:
        raise RuntimeError("홈페이지에서 '판매 베스트 상품' 진열을 찾지 못했습니다.")

    # 다음 상품 진열 블록 전까지만 잘라, 다른 메인 섹션의 상품을 섞지 않는다.
    next_start = page.find("xans-product-listmain-", start + len(SECTION_MARKER))
    section = page[start: next_start if next_start >= 0 else len(page)]
    matches = list(re.finditer(r'id="anchorBoxId_(\d+)"', section))
    products = []
    for rank, match in enumerate(matches, start=1):
        block_end = matches[rank].start() if rank < len(matches) else len(section)
        block = section[match.start():block_end]
        link = re.search(r'<a href="([^"]+)"', block)
        name = re.search(r'<p class="name">(.*?)</p>', block, re.DOTALL)
        price = re.search(r'data-price="[^"]*\^(\d+)"', block)
        if not link or not name or not price:
            continue
        products.append(
            {
                "rank": rank,
                "product_no": match.group(1),
                "name": text_without_tags(name.group(1)).replace("상품명 : ", ""),
                "cost": int(price.group(1)),
                "source_url": urljoin(HOME_URL, html.unescape(link.group(1))),
                "best_evidence": {
                    "section_title": SECTION_TITLE,
                    "signal": "홈페이지 공개 진열 순서",
                    "sales_volume_disclosed": False,
                    "note": "판매량은 공개되지 않아 추정하지 않음",
                },
                "status": "needs_product_page_verification",
            }
        )
    if not products:
        raise RuntimeError("판매 베스트 상품 블록에서 상품을 추출하지 못했습니다.")
    return products


def main() -> None:
    parser = argparse.ArgumentParser(description="부산코코상회 판매 베스트 상품 조사")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research" / "cocomart-bests.json",
        help="조사 결과 JSON 경로",
    )
    args = parser.parse_args()
    products = discover()
    payload = {
        "source": "부산코코상회",
        "source_url": HOME_URL,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "section_title": SECTION_TITLE,
        "sales_volume_disclosed": False,
        "products": products,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] 판매 베스트 상품 {len(products)}개 기록: {args.output}")


if __name__ == "__main__":
    main()
