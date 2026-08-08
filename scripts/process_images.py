# 원본 상품 사진 → 스마트스토어 규격 가공
#   - 정사각형(흰 배경 패딩), 1000x1000 리사이즈
#   - EXIF 제거, JPEG 변환
#   - 최소 해상도 미달 이미지는 경고 후 업스케일
#
# 네이버 이미지 권장 규격: 정사각형 1000x1000 (최소 300x300), JPEG/PNG,
# 과도한 텍스트/테두리/워터마크 금지 (SKILL.md 참고)
#
# 사용법:
#   python3 scripts/process_images.py <입력디렉터리> <출력디렉터리> [--size 1000]

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

TARGET_SIZE = 1000
MIN_SIZE = 300
JPEG_QUALITY = 90
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic"}


def process_one(src: Path, dst_dir: Path, size: int) -> dict:
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
    warning = None
    if max(w, h) < MIN_SIZE:
        warning = f"원본 해상도 {w}x{h} — 최소 {MIN_SIZE}px 미달, 업스케일됨 (화질 저하 주의)"

    # 정사각형 흰 배경 캔버스에 중앙 배치
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    canvas = canvas.resize((size, size), Image.LANCZOS)

    dst = dst_dir / (src.stem + ".jpg")
    canvas.save(dst, "JPEG", quality=JPEG_QUALITY)  # save 시 EXIF 미전달 → 제거됨

    return {
        "source": str(src),
        "output": str(dst),
        "original_size": [w, h],
        "output_size": [size, size],
        "warning": warning,
    }


def process_dir(input_dir: Path, output_dir: Path, size: int = TARGET_SIZE) -> list[dict]:
    files = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT
    )
    if not files:
        raise FileNotFoundError(f"{input_dir} 에 처리할 이미지가 없습니다.")

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for src in files:
        try:
            results.append(process_one(src, output_dir, size))
        except Exception as e:
            results.append({"source": str(src), "output": None, "error": str(e)})
    return results


def main():
    parser = argparse.ArgumentParser(description="상품 이미지 스마트스토어 규격 가공")
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--size", type=int, default=TARGET_SIZE)
    args = parser.parse_args()

    results = process_dir(Path(args.input_dir), Path(args.output_dir), args.size)
    print(json.dumps(results, ensure_ascii=False, indent=2))

    failed = [r for r in results if r.get("error")]
    ok_count = len(results) - len(failed)
    print(f"\n[+] {ok_count}/{len(results)}개 가공 완료 → {args.output_dir}", file=sys.stderr)
    sys.exit(1 if failed and not ok_count else 0)


if __name__ == "__main__":
    main()
