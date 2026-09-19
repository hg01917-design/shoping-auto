"""Extract one MYBOX ZIP subfolder with repaired CP949 names.

The supplied archive stores Korean member names without the UTF-8 flag.  This
tool decodes only the requested folder and writes files under a safe local
destination, so no mojibake path is created in the workspace.
"""

import argparse
import shutil
import zipfile
from pathlib import Path


def repaired_name(name: str) -> str:
    try:
        return name.encode("cp437").decode("cp949")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("source_folder", help="CP949-corrected folder name in the archive")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    prefix = args.source_folder.rstrip("/") + "/"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with zipfile.ZipFile(args.zip_path) as archive:
        for info in archive.infolist():
            corrected = repaired_name(info.filename)
            if info.is_dir() or not corrected.startswith(prefix):
                continue
            relative = Path(corrected[len(prefix) :])
            if len(relative.parts) != 1 or relative.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            target = args.output_dir / relative.name
            with archive.open(info) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            extracted += 1
    if not extracted:
        raise SystemExit(f"No images found for: {args.source_folder}")
    print(f"[+] {extracted} images extracted to {args.output_dir}")


if __name__ == "__main__":
    main()
