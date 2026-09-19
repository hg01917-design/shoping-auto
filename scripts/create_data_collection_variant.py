"""등록 상품에서 검색 데이터 수집용 별도 상품 폴더를 준비한다.

원본 상품의 등록 이력은 보존하고, 새 슬러그에 별도 listing/status를 만든다.
실제 구성·용량·고시 정보는 원본 그대로 유지하며 상품명·검색 의도·이미지 레이아웃만
실험 대상으로 바꾼다. 생성 후에는 process_images.py의 --layout-seed로 이미지를
다시 만들고 register_product.py로 새 폴더만 등록한다.
"""

import argparse
import html
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="검색 데이터 수집용 상품 변형 폴더 생성")
    parser.add_argument("source_slug", help="기존 products/<slug> 이름")
    parser.add_argument("variant_slug", help="새 products/<slug> 이름")
    parser.add_argument("--title", required=True, help="별도 등록 상품명")
    parser.add_argument("--primary-keyword", required=True, help="별도 등록의 핵심 검색 의도")
    parser.add_argument("--tags", help="쉼표로 구분한 판매자 태그 (생략 시 원본 태그 유지)")
    parser.add_argument("--layout-seed", required=True, help="대표/상세 이미지 레이아웃 식별값")
    args = parser.parse_args()

    source_dir = ROOT / "products" / args.source_slug
    variant_dir = ROOT / "products" / args.variant_slug
    source_listing_path = source_dir / "output" / "listing.json"
    if not source_listing_path.exists():
        raise FileNotFoundError(f"원본 listing.json이 없습니다: {source_listing_path}")
    if variant_dir.exists():
        raise FileExistsError(f"이미 존재하는 변형 폴더입니다: {variant_dir}")

    shutil.copytree(source_dir, variant_dir)
    listing_path = variant_dir / "output" / "listing.json"
    listing = load_json(listing_path)
    tags = (
        [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        if args.tags is not None
        else list(listing.get("sellerTags", []))
    )
    if not 1 <= len(tags) <= 10 or len(tags) != len(set(tags)):
        raise ValueError("판매자 태그는 중복 없이 1~10개여야 합니다.")

    keyword = html.escape(args.primary_keyword)
    title = html.escape(args.title)
    intro = (
        '<p style="font-size:19px;line-height:1.8;margin:0 0 18px;">'
        f'<strong>{keyword}</strong>를 찾는 분을 위해 준비한 {title}입니다. '
        '구성 수량과 급여·보관 방법은 제품 라벨을 기준으로 확인해 주세요.'
        '</p>'
    )
    listing["name"] = args.title
    listing["sellerTags"] = tags
    listing["detailKeywords"] = [args.primary_keyword]
    listing["detailContent"] = intro + listing.get("detailContent", "")
    listing["dataCollectionVariant"] = {
        "sourceSlug": args.source_slug,
        "primaryKeyword": args.primary_keyword,
        "layoutSeed": args.layout_seed,
        "createdAt": datetime.now().isoformat(),
    }
    write_json(listing_path, listing)

    write_json(
        variant_dir / "status.json",
        {
            "status": "prepared",
            "data_collection_variant_of": args.source_slug,
            "title": args.title,
            "primary_keyword": args.primary_keyword,
            "layout_seed": args.layout_seed,
            "created_at": datetime.now().isoformat(),
        },
    )
    write_json(
        variant_dir / "output" / "variant-record.json",
        {
            "source_slug": args.source_slug,
            "variant_slug": args.variant_slug,
            "purpose": "search-data-collection",
            "title": args.title,
            "primary_keyword": args.primary_keyword,
            "seller_tags": tags,
            "layout_seed": args.layout_seed,
            "created_at": datetime.now().isoformat(),
        },
    )
    print(f"[+] 변형 폴더 생성: {variant_dir}")


if __name__ == "__main__":
    main()
