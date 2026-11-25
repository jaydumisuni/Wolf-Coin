#!/usr/bin/env python3
"""Stage the exact official embeddable Windows Python distributable.

It is a local release ingredient, deliberately excluded from public Git.
The private Wolf-Coin backend is supplied independently and is not included.
"""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile
import shutil

EXPECTED = "d297e5ff019966817ad8502465176139f2d3d840fa4ed84b13bed399a6ab1f15"
BACKEND_PATHS = (
    r"..\app\backend-runtime",
    r"..\app.asar.unpacked\backend-runtime",
)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "python-runtime")
    args = parser.parse_args()
    archive = args.archive.resolve()
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != EXPECTED:
        parser.error(f"Archive SHA-256 mismatch: {actual}")
    dest = args.out.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as package:
        for file in package.infolist():
            if file.is_dir():
                continue
            # The official embeddable release is a flat archive.
            if Path(file.filename).name != file.filename:
                parser.error(f"Archive contains non-flat path {file.filename}")
            with package.open(file) as inp, (dest / file.filename).open("wb") as out:
                shutil.copyfileobj(inp, out)
    pth = dest / "python314._pth"
    content = pth.read_text(encoding="utf-8")
    assert "python314.zip" in content, "CPython standard library archive path missing"
    for entry in BACKEND_PATHS:
        if entry not in content:
            content += "\n" + entry + "\n"
    # Do not silently enable site packages, user site, or host python paths.
    pth.write_text(content, encoding="utf-8")
    for name in ("python.exe", "python314.dll", "python314.zip", "_sqlite3.pyd",
                 "sqlite3.dll", "LICENSE.txt"):
        if not (dest / name).is_file():
            raise RuntimeError(f"Missing expected official runtime file: {name}")
    print(f"WOLF_WINDOWS_EMBEDDED_PYTHON_STAGE_PASS archive_sha={actual} files={len(list(dest.iterdir()))}")
    print("python314._pth=" + repr(content))

if __name__ == "__main__":
    main()
