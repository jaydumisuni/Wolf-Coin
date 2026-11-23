"""Frozen three-window verification with explicit historical CSV hashes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .cli import _write_private
from .odds_replay import ReplayRefused, ReplayPolicy, load_season
from .walkforward import walk_forward, render_walkforward_html


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(prog="wolf-lab-walkforward",
                              description="Three historical seasons; only paper/research")
    for name in ("train","validation","final"):
        p.add_argument("--"+name,type=Path,required=True)
        p.add_argument("--"+name+"-sha256",required=True)
    p.add_argument("--report-json",type=Path,required=True)
    p.add_argument("--report-html",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        if a.report_json.resolve()==a.report_html.resolve():
            raise ReplayRefused("distinct private report destinations required")
        train=load_season(a.train,expected_sha256=a.train_sha256)
        validation=load_season(a.validation,expected_sha256=a.validation_sha256)
        final=load_season(a.final,expected_sha256=a.final_sha256)
        report=walk_forward(train,validation,final,policy=ReplayPolicy())
        _write_private(a.report_json,json.dumps(report,indent=2,sort_keys=True)+"\n")
        _write_private(a.report_html,render_walkforward_html(report))
        print(json.dumps({
            "status":"HISTORICAL_RESEARCH_ONLY",
            "validation_decision":report["decision"],
            "final_bets":report["final"]["bets"],
            "final_virtual_net":report["final"]["net_virtual_ZMW"],
            "future_profit_proven":False,
            "live_admission":False,
            "report_json":str(a.report_json.resolve()),
            "report_html":str(a.report_html.resolve()),
        },sort_keys=True))
        return 0
    except (ReplayRefused, OSError, ValueError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc),"live_admission":False}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
