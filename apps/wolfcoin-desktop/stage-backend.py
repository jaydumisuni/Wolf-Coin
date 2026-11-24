#!/usr/bin/env python3
"""Stage the exact owner-controlled Wolf-Coin backend Python modules locally.

Do not commit or publish the staged source. The native host/packages consume the
locally staged copy; the owner's separately developed backend branch remains untouched.
"""
import argparse
import hashlib
import shutil
from pathlib import Path

FILES = (
    "wolf_app/__init__.py",
    "wolf_app/bridge.py",
    "wolf_app/backup.py",
    "wolf_app/store.py",
    "wolf_app/contracts.py",
    "wolf_app/context_router.py",
    "wolf_core/__init__.py",
    "wolf_core/contracts.py",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", default=Path(__file__).resolve().parent / "backend-runtime", type=Path)
    a = parser.parse_args()
    src = a.source.resolve()
    dst = a.output.resolve()
    if src == dst or dst.is_relative_to(src) or src.is_relative_to(dst):
        parser.error("backend source and stage must remain separate")
    for filename in FILES:
        path = src / filename
        if not path.is_file():
            parser.error(f"source missing {filename}")
    for filename in FILES:
        p = dst / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / filename, p)
        orig = hashlib.sha256((src / filename).read_bytes()).digest()
        copied = hashlib.sha256(p.read_bytes()).digest()
        if orig != copied:
            raise RuntimeError("backend source stage does not match: " + filename)
    print(f"STAGED_OWNER_BACKEND_MATCH {len(FILES)} modules -> {dst}")


if __name__ == "__main__":
    main()
