#!/usr/bin/env python3
"""Build Wolf-Coin frontend with owner-held D-XQT; no private runtime in Git."""
from __future__ import annotations
from pathlib import Path
import argparse
import os

def build() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--dxqt-js",type=Path)
    parser.add_argument("--desktop",type=Path)
    parser.add_argument("--android",type=Path)
    parser.add_argument("--preview",action="store_true")
    args=parser.parse_args()
    here=Path(__file__).resolve().parent
    src=(here/"ui-template.html").read_text(encoding="utf-8")
    slot="/* WOLF_PRIVATE_DXQT_INSERT */"
    if src.count(slot)!=1:
        raise ValueError("D-XQT private insertion marker missing or duplicated")
    if args.preview:
        private_js="window.WOLF_DXQT={status:'not_bundled',error:'Private D-XQT not available',ready:Promise.reject(new Error('Private D-XQT not available'))};window.WOLF_DXQT.ready.catch(()=>{});"
    else:
        if args.dxqt_js is None or not args.dxqt_js.is_file():
            raise ValueError("Provide --dxqt-js with the locally approved private runtime; do not commit it")
        private_js=args.dxqt_js.read_text(encoding="utf-8")
        if len(private_js)<300000 or "const GZIP_B64=" not in private_js or "window.WOLF_DXQT=engine" not in private_js:
            raise ValueError("Private D-XQT payload failed static validation")
        if "</script" in private_js.lower():
            raise ValueError("Unexpected HTML script terminator in private D-XQT JS")
    html=src.replace(slot,private_js,1)
    portfolio_dir=here.parent/"wolfcoin-portfolio"
    portfolio_core=(portfolio_dir/"portfolio.js").read_text(encoding="utf-8")
    portfolio_ui=(portfolio_dir/"ui.js").read_text(encoding="utf-8")
    for script in (portfolio_core,portfolio_ui):
        if "</script" in script.lower():
            raise ValueError("Portfolio scripts contain script terminator")
    html=html.replace("</body>", "<script>\n"+portfolio_core+"\n</script>\n<script>\n"+portfolio_ui+"\n</script>\n</body>",1)

    if args.desktop:
        args.desktop.parent.mkdir(parents=True,exist_ok=True)
        args.desktop.write_text(html,encoding="utf-8")
    if args.android:
        bridge=here.parent/"wolfcoin-android"/"wolf_android_bridge.js"
        js=bridge.read_text(encoding="utf-8")
        if "</script" in js.lower():
            raise ValueError("Android host bridge contains an HTML script terminator")
        android=html.replace("<head>","<head>\n<script>\n"+js+"\n</script>\n",1)
        args.android.parent.mkdir(parents=True,exist_ok=True)
        args.android.write_text(android,encoding="utf-8")
    print("Wolf-Coin frontend assembled:",len(html),"bytes; private runtime",not args.preview)

if __name__=="__main__":
    build()
