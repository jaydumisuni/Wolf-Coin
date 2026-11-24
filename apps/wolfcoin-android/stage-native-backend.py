#!/usr/bin/env python3
"""Copy the exact owner-controlled native Python backend into the Android build.

The staged backend is a local build ingredient, not public frontend source.
No permanent fallback runtime or product capability restrictions are added.
"""
import argparse
import hashlib
import shutil
from pathlib import Path

FILES=(
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
    cmd=argparse.ArgumentParser()
    cmd.add_argument("--source",type=Path,required=True)
    cmd.add_argument("--output",type=Path,default=Path(__file__).resolve().parent/"app/src/main/python")
    args=cmd.parse_args()
    src=args.source.resolve()
    dst=args.output.resolve()
    if src==dst or src.is_relative_to(dst) or dst.is_relative_to(src):
        cmd.error("Source and destination must be distinct")
    for name in FILES:
        if not (src/name).is_file():
            cmd.error("Missing owner backend file "+name)
    for name in FILES:
        dst_path=dst/name
        dst_path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src/name,dst_path)
        if hashlib.sha256(dst_path.read_bytes()).digest()!=hashlib.sha256((src/name).read_bytes()).digest():
            raise RuntimeError("Staged backend SHA mismatch: "+name)
    print("STAGED_ANDROID_OWNER_BACKEND_MATCH "+str(len(FILES))+" modules")

if __name__=="__main__":
    main()
