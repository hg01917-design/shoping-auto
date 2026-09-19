# 원본 상품 사진 → 스마트스토어 규격 가공
#   - 대표 이미지만 정사각형 흰 배경으로 정리 (원본보다 크게 확대하지 않음)
#   - 보조/상세 이미지는 원본 비율을 유지해 흰 여백으로 내용이 작아지지 않게 함
#   - EXIF 제거, JPEG 변환, 원본/결과 해시 기록
#
# 네이버 이미지 권장 규격: 정사각형 1000x1000 (최소 300x300), JPEG/PNG,
# 과도한 텍스트/테두리/워터마크 금지 (SKILL.md 참고)
#
# 사용법:
#   python3 scripts/process_images.py <입력디렉터리> <출력디렉터리> [--size 1000]

import argparse
import colorsys
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageOps

TARGET_SIZE = 1000
MIN_SIZE = 300
JPEG_QUALITY = 90
# 대표 이미지의 제품이 모바일 화면에서 작게 보이지 않도록 한다. 원본 테두리·배경을
# 포함한 제품 사진을 크게 배치하고, 재구성 요소는 바깥 여백에만 아주 작게 사용한다.
REPRESENTATIVE_MARGIN = 42
DETAIL_MARGIN = 22
MAX_REPRESENTATIVE_UPSCALE = 1.6
# 원본 바깥의 단색 빈 여백만 검증해 제거한 경우에는 제품 픽셀을 더 크게
# 보여 줄 수 있다. 포장·라벨 영역을 손대지 않는 조건에서만 적용한다.
MAX_CROPPED_REPRESENTATIVE_UPSCALE = 2.0
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic"}


def file_sha256(path: Path) -> str:
    """가공 이력 검증용 SHA-256. 중복 회피 목적의 변조에는 사용하지 않는다."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resize_down_only(img: Image.Image, max_width: int) -> Image.Image:
    """원본보다 크게 키우지 않고, 폭이 큰 이미지만 축소한다."""
    width, height = img.size
    if width <= max_width:
        return img
    scaled_height = round(height * (max_width / width))
    return img.resize((max_width, scaled_height), Image.LANCZOS)


def save_jpeg(img: Image.Image, path: Path) -> dict:
    # 원본 촬영 정보·위치 정보 등 EXIF를 명시적으로 비운 새 JPEG로 저장한다.
    # 제품 이미지의 시각 내용은 이 단계에서 변경하지 않는다.
    img.save(path, "JPEG", quality=JPEG_QUALITY, exif=b"", optimize=True)
    return {
        "path": str(path),
        "size": list(img.size),
        "sha256": file_sha256(path),
    }


def creative_palette(source_digest: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """원본별 강조색을 쓰되, 전체는 차분한 뉴트럴 톤으로 유지한다."""
    hue = (int(source_digest[:6], 16) % 360) / 360
    accent = tuple(round(value * 255) for value in colorsys.hsv_to_rgb(hue, 0.30, 0.64))
    background = (250, 248, 244)
    return background, accent


def crop_plain_outer_margin(
    img: Image.Image,
) -> Tuple[Image.Image, Optional[Tuple[int, int, int, int]]]:
    """거의 흰색인 바깥 여백만 찾아 대표 사진의 제품 비율을 높인다.

    포장·로고·라벨 안쪽은 분석하거나 수정하지 않는다. 테두리에서 충분히 떨어진
    비백색 영역이 있을 때만 그 바깥의 평평한 흰 영역을 제거하고, 오검출 방지를
    위해 12px의 원본 여백을 남긴다.
    """
    reference = Image.new("RGB", img.size, (250, 250, 250))
    diff = ImageChops.difference(img.convert("RGB"), reference).convert("L")
    content = diff.point(lambda value: 255 if value > 18 else 0)
    bbox = content.getbbox()
    if bbox is None:
        return img, None

    left, top, right, bottom = bbox
    width, height = img.size
    # 원본 테두리까지 닿는 사진이나, 제거할 여백이 아주 적은 사진은 그대로 둔다.
    if min(left, top, width - right, height - bottom) < 18:
        return img, None

    pad = 12
    crop_box = (
        max(0, left - pad),
        max(0, top - pad),
        min(width, right + pad),
        min(height, bottom + pad),
    )
    cropped = img.crop(crop_box)
    if cropped.width < MIN_SIZE or cropped.height < MIN_SIZE:
        return img, None
    return cropped, crop_box


def compose_creative_layout(
    img: Image.Image,
    source_digest: str,
    size: int,
    is_representative: bool,
    crop_box: Optional[Tuple[int, int, int, int]] = None,
    layout_seed: str = "",
) -> Image.Image:
    """원본 사진을 그대로 재저장하지 않고, 새 배경·프레임·여백으로 재구성한다.

    제품 포장·라벨·색상·구성 픽셀은 생성·보정·변형하지 않고 그대로 삽입한다.
    바뀌는 것은 사진 밖의 배경·프레임·여백뿐이며, 원본보다 크게 확대하지 않는다.
    """
    layout_digest = hashlib.sha256(f"{source_digest}:{layout_seed}".encode()).hexdigest()
    background, accent = creative_palette(layout_digest)
    width, height = img.size
    if is_representative:
        canvas = Image.new("RGB", (size, size), background)
        draw = ImageDraw.Draw(canvas)
        # 제품을 뒤집지 않고 배경 도형의 위치만 좌·우 다르게 구성한다.
        mirrored_background = int(layout_digest[6:8], 16) % 2 == 1
        if mirrored_background:
            ellipse_box = (-size * 0.05, -size * 0.10, size * 0.28, size * 0.23)
        else:
            ellipse_box = (size * 0.72, -size * 0.10, size * 1.05, size * 0.23)
        # 이전처럼 큰 원형 배경이 제품 사진보다 눈에 띄지 않도록, 테두리 밖에만
        # 작은 포인트를 둔다.
        draw.ellipse(ellipse_box, fill=accent)
        photo = img.copy()
        # 500px 이상인 원본은 모바일 대표 이미지에서 제품이 충분히 보이도록
        # 최대 1.6배까지 고품질 리사이즈한다. 단색 외곽 여백만 제거한 사진은
        # 포장 자체를 바꾸지 않고도 제품 비율을 회복할 수 있어 최대 2배까지 허용한다.
        max_photo = size - REPRESENTATIVE_MARGIN * 2
        source_long_edge = max(photo.width, photo.height)
        upscale_limit = (
            MAX_CROPPED_REPRESENTATIVE_UPSCALE
            if crop_box is not None
            else MAX_REPRESENTATIVE_UPSCALE
        )
        if (source_long_edge >= 450 or crop_box is not None) and source_long_edge < max_photo:
            target_long_edge = min(max_photo, round(source_long_edge * upscale_limit))
            scale = target_long_edge / source_long_edge
            photo = photo.resize(
                (round(photo.width * scale), round(photo.height * scale)), Image.LANCZOS
            )
        if photo.width > max_photo or photo.height > max_photo:
            scale = min(max_photo / photo.width, max_photo / photo.height)
            photo = photo.resize(
                (round(photo.width * scale), round(photo.height * scale)), Image.LANCZOS
            )
        card = Image.new("RGB", (photo.width + 8, photo.height + 8), (255, 255, 255))
        horizontal_offset = 18 if int(layout_digest[8:10], 16) % 2 else -18
        x = max(0, min(size - card.width, (size - card.width) // 2 + horizontal_offset))
        y = (size - card.height) // 2
        canvas.paste(card, (x, y))
        canvas.paste(photo, (x + 4, y + 4))
        return canvas

    # 상세·라벨 이미지는 본문 가독성을 유지한 채 독자적인 카드 레이아웃으로 만든다.
    canvas = Image.new(
        "RGB", (width + DETAIL_MARGIN * 2, height + DETAIL_MARGIN * 2), background
    )
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, canvas.width, 8), fill=accent)
    draw.rectangle((0, canvas.height - 8, canvas.width, canvas.height), fill=accent)
    if int(layout_digest[6:8], 16) % 2 == 1:
        draw.rectangle((0, 0, 8, canvas.height), fill=accent)
    else:
        draw.rectangle((canvas.width - 8, 0, canvas.width, canvas.height), fill=accent)
    card = Image.new("RGB", (width + 4, height + 4), (255, 255, 255))
    canvas.paste(card, (DETAIL_MARGIN - 2, DETAIL_MARGIN - 2))
    canvas.paste(img, (DETAIL_MARGIN, DETAIL_MARGIN))
    return canvas


def load_semantic_cut_points(src: Path, height: int) -> list[int]:
    """시각 검토가 끝난 상세 원본에만 사람이 정한 절단 지점을 적용한다.

    자동 높이 기준 분할은 제목·그래프·설명을 끊을 수 있으므로 사용하지 않는다.
    ``input/image-sections.json``의 절단점은 반드시 원본의 여백 구간을 사람이
    확인한 뒤 기록한다.
    """
    plan_candidates = (src.parent / "image-sections.json", src.parent.parent / "image-sections.json")
    plan_path = next((path for path in plan_candidates if path.exists()), None)
    if plan_path is None:
        return []
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        entry = plan.get(src.name, {})
        points = entry.get("cut_points", []) if isinstance(entry, dict) else []
        points = [int(point) for point in points]
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise ValueError(f"상세 이미지 분할 계획 오류: {plan_path}: {error}") from error

    if points != sorted(set(points)) or any(point <= 0 or point >= height for point in points):
        raise ValueError(f"상세 이미지 절단점은 0과 {height} 사이의 오름차순 정수여야 합니다: {src.name}")
    return points


def process_one(
    src: Path, dst_dir: Path, size: int, is_representative: bool, layout_seed: str = ""
) -> dict:
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)  # EXIF 회전 반영 후 메타데이터 제거

    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        img_rgba = img.convert("RGBA")
        background.paste(img_rgba, mask=img_rgba.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    source_digest = file_sha256(src)
    warning = None
    if min(w, h) < MIN_SIZE:
        warning = (
            f"원본 해상도 {w}x{h} — 짧은 변이 최소 {MIN_SIZE}px 미달. "
            "자동 확대하지 않았으므로 고해상도 부산코코상회 원본을 다시 확보해야 함"
        )

    outputs = []
    interleave_outputs = False
    if is_representative:
        # 대표 이미지는 1:1 비율로 보이게 하되, 500px 원본을 1000px로
        # 단순 확대하는 방식은 흐림만 만들므로 원본보다 크게 키우지 않는다.
        representative, crop_box = crop_plain_outer_margin(img)
        processed = resize_down_only(representative, size)
        processed = compose_creative_layout(
            processed, source_digest, size, True, crop_box, layout_seed
        )
        transform = (
            "representative_crop_plain_outer_margin_then_large_product_layout_up_to_2x"
            if crop_box is not None
            else "representative_large_product_layout_up_to_1.6x_for_450px_sources"
        )
        outputs.append(save_jpeg(processed, dst_dir / (src.stem + ".jpg")))
    else:
        # 라벨/상세 원본은 정사각형 여백을 넣으면 세로형 정보가 매우 작아진다.
        # 폭이 1000px를 넘는 경우만 축소하고 세로 비율은 그대로 유지한다. 자동 분할은
        # 하지 않으며, 시각 검토된 계획이 있는 경우에만 완결된 콘텐츠 블록으로 자른다.
        cut_points = load_semantic_cut_points(src, h)
        boundaries = [0, *cut_points, h]
        for section_index, (top, bottom) in enumerate(zip(boundaries, boundaries[1:]), start=1):
            section = img.crop((0, top, w, bottom))
            processed = resize_down_only(section, size)
            processed = compose_creative_layout(
                processed, source_digest, size, False, layout_seed=layout_seed
            )
            suffix = f"__section-{section_index:02d}" if cut_points else ""
            outputs.append(save_jpeg(processed, dst_dir / f"{src.stem}{suffix}.jpg"))
        interleave_outputs = bool(cut_points)
        transform = (
            "detail_semantic_sections_visual_review"
            if cut_points
            else "detail_creative_recomposition_preserve_full_length_no_split"
        )

    return {
        "source": str(src),
        # output은 기존 호출부와의 호환을 위한 첫 파일이며, outputs가 실제
        # 업로드할 분할 파일 전체 목록이다.
        "output": outputs[0]["path"],
        "outputs": outputs,
        "original_size": [w, h],
        "representative_crop_box": list(crop_box) if is_representative and crop_box else None,
        "output_size": outputs[0]["size"] if len(outputs) == 1 else None,
        "transform": transform,
        "layout_seed": layout_seed or None,
        "source_sha256": source_digest,
        "output_sha256": outputs[0]["sha256"] if len(outputs) == 1 else None,
        "interleave_outputs": interleave_outputs,
        "warning": warning,
    }


def process_dir(
    input_dir: Path, output_dir: Path, size: int = TARGET_SIZE, layout_seed: str = ""
) -> list[dict]:
    files = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT
    )
    if not files:
        raise FileNotFoundError(f"{input_dir} 에 처리할 이미지가 없습니다.")

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, src in enumerate(files):
        try:
            results.append(
                process_one(
                    src, output_dir, size, is_representative=index == 0, layout_seed=layout_seed
                )
            )
        except Exception as e:
            results.append({"source": str(src), "output": None, "error": str(e)})
    return results


def main():
    parser = argparse.ArgumentParser(description="상품 이미지 스마트스토어 규격 가공")
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--size", type=int, default=TARGET_SIZE)
    parser.add_argument(
        "--layout-seed",
        default="",
        help="제품 픽셀은 유지한 채 배경·프레임·대표 이미지 배치를 다르게 만드는 식별값",
    )
    args = parser.parse_args()

    results = process_dir(
        Path(args.input_dir), Path(args.output_dir), args.size, args.layout_seed
    )
    manifest_path = Path(args.output_dir) / "processing-manifest.json"
    manifest_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))

    failed = [r for r in results if r.get("error")]
    ok_count = len(results) - len(failed)
    print(f"\n[+] {ok_count}/{len(results)}개 가공 완료 → {args.output_dir}", file=sys.stderr)
    sys.exit(1 if failed and not ok_count else 0)


if __name__ == "__main__":
    main()
