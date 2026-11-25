#!/usr/bin/env python3
"""Build the owner-only Wolf-Coin per-user Windows development installer.

Uses the native NSIS compiler on Linux or Windows. Requires the verified
Windows payload to already be assembled; does not install or launch software.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

NEEDED = (
    "Wolf-Coin.exe",
    "resources/app/main.cjs",
    "resources/app/backend_host.cjs",
    "resources/app/backend-runtime/wolf_app/bridge.py",
    "resources/app/app.html",
    "resources/python/python.exe",
    "resources/python/python314.dll",
    "resources/python/LICENSE.txt",
)

def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--payload", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--makensis", type=Path, required=True)
    cli.add_argument("--nsisdir", type=Path, required=True)
    a = cli.parse_args()
    root = a.payload.resolve()
    dest = a.output.resolve()
    source = Path(__file__).with_name("wolfcoin-windows.nsi.in")
    for name in NEEDED:
        if not (root / name).is_file():
            cli.error("Package missing " + name)
    installer_script = source.read_text(encoding="utf-8")
    if installer_script.count("@@SOURCE@@") < 1 or installer_script.count("@@OUTPUT@@") < 1:
        cli.error("Expected installer placeholders not present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wolf-nsis-") as scratch:
        template = Path(scratch) / "installer.nsi"
        template.write_text(installer_script.replace("@@SOURCE@@",str(root))
                            .replace("@@OUTPUT@@",str(dest)), encoding="utf-8")
        env = dict(os.environ)
        env["NSISDIR"] = str(a.nsisdir.resolve())
        subprocess.run([str(a.makensis.resolve()), "-V2", "-INPUTCHARSET", "UTF8",
                        str(template)], env=env, check=True)
    if not dest.is_file() or dest.stat().st_size < 1024 * 1024:
        raise RuntimeError("The NSIS compiler did not deliver a complete installer")
    with dest.open("rb") as f:
        if f.read(2) != b"MZ":
            raise RuntimeError("Invalid Windows installer header")
    print(f"WOLF_NATIVE_NSIS_INSTALLER_BUILT {dest.stat().st_size} bytes: {dest}")

if __name__ == "__main__":
    main()
