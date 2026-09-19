"""공통 상세페이지 안내 이미지를 스마트스토어 CDN에 올리고 URL을 기록한다.

사용법:
    python3 scripts/upload_detail_notices.py

이 스크립트는 상품 대표·추가 이미지를 바꾸지 않는다. 공통 상세 상단/하단
안내 카드의 CDN URL만 config/detail-notices.json에 기록한다.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from register_product import upload_images


ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT / "assets" / "detail-notices"
CONFIG_PATH = ROOT / "config" / "detail-notices.json"
ASSETS = (
    ASSET_DIR / "shipping-priority-v1.png",
    ASSET_DIR / "stock-notice-v1.png",
)


def main() -> None:
    missing = [str(path) for path in ASSETS if not path.exists()]
    if missing:
        raise FileNotFoundError("공통 안내 이미지가 없습니다: " + ", ".join(missing))
    urls = upload_images(ROOT, [str(path) for path in ASSETS])
    if len(urls) != 2:
        raise RuntimeError(f"안내 이미지 업로드 결과가 2장이 아닙니다: {urls}")
    payload = {
        "shippingPriorityUrl": urls[0],
        "stockNoticeUrl": urls[1],
        "uploadedAt": datetime.now().isoformat(),
        "sourceAssets": [str(path.relative_to(ROOT)) for path in ASSETS],
        "copy": {
            "shipping": "평일 낮 12시 이전 결제 완료 주문은 출고를 우선 진행합니다. 재고·입고 상황 및 주문량에 따라 출고 일정이 달라질 수 있으며 변동 시 문자로 안내드립니다.",
            "stock": "재고 변동 또는 품절이 확인되면 문자로 먼저 안내드립니다. 대체 상품 확인 또는 주문 취소를 선택하실 수 있으며, 재고 확인·입고 과정에 따라 배송 준비 기간이 길어질 수 있습니다.",
        },
    }
    CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
