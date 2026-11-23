"""wolf-lab: reproduce one frozen historical odds evaluation locally.

Intended only for private/academic research on lawfully obtained datasets.
No live betting, credential, external network, or trade action exists here.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from .odds_replay import ReplayRefused, ReplayPolicy, load_season, replay, render_html


def _write_private(path: Path, data: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.is_symlink() or path.exists():
        raise ReplayRefused("research output must be a new file, no overwrite")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wolf-lab", description="Wolf-Coin historical paper replay")
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--train-sha256", required=True)
    parser.add_argument("--holdout-sha256", required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--report-html", type=Path, required=True)
    args=parser.parse_args(argv)
    try:
        if args.report_json.resolve() == args.report_html.resolve():
            raise ReplayRefused("JSON and HTML reports cannot share destination")
        train=load_season(args.train,expected_sha256=args.train_sha256)
        holdout=load_season(args.holdout,expected_sha256=args.holdout_sha256)
        result=replay(train,holdout,policy=ReplayPolicy())
        _write_private(args.report_json,json.dumps(result,sort_keys=True,indent=2)+"\n")
        _write_private(args.report_html,render_html(result))
        print(json.dumps({
            "status":"HISTORICAL_RESEARCH_ONLY",
            "json":str(args.report_json.resolve()),"html":str(args.report_html.resolve()),
            "bets":result["bets"],"net_virtual_ZMW":result["net_virtual_ZMW"],
            "model_brier":result["model_brier"],
            "market_brier":result["market_no_vig_brier"],
            "profit_proven":False, "live_ready":False
        },sort_keys=True))
        return 0
    except (ReplayRefused, OSError, ValueError) as exc:
        print(json.dumps({"status":"BLOCKED","error":str(exc),"live_ready":False}),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
