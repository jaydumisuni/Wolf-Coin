"""Private Wolf-Coin research-candidate dataset and CPU comparison.

One purpose: ground the SUP Director in exact, time-lagged data. Does not
assert external source qualification, legal automated access, or training
authority. No betting/trading network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

from wolf_lab.cli import _write_private
from wolf_lab.odds_replay import ReplayRefused
from wolf_lab.learning_dataset import FEATURE_NAMES, load_verified, materialize
from wolf_lab.forecast_cpu import compare


def _json_digest(object_:object) -> str:
    return hashlib.sha256(json.dumps(object_,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def rows_to_dict(groups):
    return [
        [{"day":r.day,"season":r.season,"match_id":r.match_id,
          "features":r.features,"market":r.market,"label":r.label,
          "prices":r.prices,"home_prior_games":r.home_prior_games,
          "away_prior_games":r.away_prior_games} for r in rows]
        for rows in groups
    ]


def evaluate_four(paths, hashes, *, source_head: str, sup_generation: str):
    if len(paths)!=4 or len(hashes)!=4:
        raise ReplayRefused("exactly four season inputs are required")
    if not isinstance(source_head,str) or re.fullmatch(r"[0-9a-f]{40}",source_head) is None:
        raise ReplayRefused("git source generation must be 40 lowercase hex chars")
    if not isinstance(sup_generation,str) or re.fullmatch(r"sha256:[0-9a-f]{64}",sup_generation) is None:
        raise ReplayRefused("SUP generation digest is required")
    seasons=("2022/23","2023/24","2024/25","2025/26")
    loaded=[load_verified(Path(p),expected_sha256=h,season=s)
            for p,h,s in zip(paths,hashes,seasons)]
    groups=materialize(tuple(loaded))
    train=groups[0]+groups[1]
    validation=groups[2]
    diagnostic=groups[3]
    report=compare(train,validation,diagnostic)
    private_rows=rows_to_dict(groups)
    features_digest=_json_digest(private_rows)
    report.update(
        source_head=source_head,
        sup_generation=sup_generation,
        season_sha256=dict(zip(seasons,hashes)),
        feature_sha256=features_digest,
        feature_schema="wolf.prior-day-market-odds.v1",
        feature_count=len(FEATURE_NAMES),
        timeline=("train: 2022/23 + 2023/24",
                  "validation: 2024/25",
                  "exposed diagnostic only: 2025/26"),
        source_truth_qualified=False,
        provider_quote_timestamps_qualified=False,
        model_status="RESEARCH_CANDIDATE_NOT_ADMITTED",
    )
    learning_package={
        "package_id":"Wolf-Coin:prior-day-1x2:"+features_digest[:24],
        "source_product":"Wolf-Coin",
        "source_generation":source_head,
        "evidence_generation":"sha256:"+features_digest,
        "capability":"pre-match football 1X2 probability research candidate",
        "scope":{"league":"English Premier League E0",
                 "seasons":list(seasons),
                 "data_fingerprint":features_digest,
                 "commercial_live_use_permitted":False,
                 "quote_timestamps_qualified":False,
                 "final_unexamined_period_available":False},
        "positive_evidence":[{"kind":"input-digest","season":s,"sha256":h} for s,h in zip(seasons,hashes)]
                            + [{"kind":"derived-prior-day-features","sha256":features_digest}],
        "negative_evidence":[{"kind":"observed-losing-baseline",
                              "source":"Wolf-Coin docs/HISTORICAL_REPLAY_PROOF_2026-11-23.md"}],
        "counter_worlds":[{"case":"post-kickoff-result-leakage",
                           "expected":"rejected by date-grouped features"}],
        "rejected_hypotheses":[{"claim":"historic Elo proves net profit","status":"rejected"}],
        "required_behavior":["only time-prior features","market-relative proper scores",
                             "abstain without independent improvement"],
        "forbidden_regressions":["live betting","silent new dataset source truth",
                                "2025/26 reclassified as untouched"],
        "transfer_scope":"Wolf-Coin research only; no cross-product source transfer",
        "source_truth_qualified":False,
        "neural_realization_allowed":False,
    }
    sup_request={
        "subject":"SUP",
        "instruction":"Compare evidence-bound neural forecasting routes on Wolf-Coin's time-safe football feature candidate. Do not train until independent source qualification and proof of legal data-use rights, then obtain fresh Tenfold worker authority. Keep financial execution disabled.",
        "target_product":"Wolf-Coin",
        "sup_generation":sup_generation,
        "autonomous_deploy":False,
        "interpretation":{
            "capability_need":"neural",
            "capability":"CPU-friendly probabilistic 1X2 forecasting on verified prior-match features",
            "baseline":{
                "metric":"validation market Brier and held-out CPU corrector Brier",
                "evidence_digest":"sha256:"+_json_digest(report)
            },
            "acceptance_criteria":[
                "only source-qualified pre-match data and independent chronology",
                "proper scoring improves over market after uncertainty bounds",
                "new genuinely untouched future period independent of exposed 2025/26",
                "CPU memory/resource budget measured on KRATOS",
            ],
            "forbidden_regressions":[
                "no financial effects or live order",
                "no training or model promotion from unqualified source truth",
                "no 2025/26 reuse as never-seen",
            ],
            "preferred_methods":[],
            "data_task":"tool","target_rows":len(train),
        },
        "learning_package":learning_package,
    }
    return report,private_rows,learning_package,sup_request


def main(argv=None) -> int:
    p=argparse.ArgumentParser(prog="wolf-lab-cpu",description="Private prior-day 1X2 CPU benchmark / SUP intake")
    for i in range(1,5):
        p.add_argument(f"--season-{i}",type=Path,required=True)
        p.add_argument(f"--sha-{i}",required=True)
    p.add_argument("--source-head",required=True)
    p.add_argument("--sup-generation",required=True)
    p.add_argument("--report-json",type=Path,required=True)
    p.add_argument("--features-json",type=Path,required=True)
    p.add_argument("--sup-intake-json",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        destinations=[args.report_json,args.features_json,args.sup_intake_json]
        if len({x.resolve() for x in destinations})!=len(destinations):
            raise ReplayRefused("outputs must be different, new private files")
        report,features,package,request=evaluate_four(
            [getattr(args,f"season_{i}") for i in range(1,5)],
            [getattr(args,f"sha_{i}") for i in range(1,5)],
            source_head=args.source_head,sup_generation=args.sup_generation)
        _write_private(args.features_json,json.dumps(features,sort_keys=True,indent=2)+"\n")
        _write_private(args.report_json,json.dumps(report,sort_keys=True,indent=2)+"\n")
        _write_private(args.sup_intake_json,json.dumps(request,sort_keys=True,indent=2)+"\n")
        print(json.dumps({
            "status":"RESEARCH_CANDIDATE_NOT_SOURCE_QUALIFIED",
            "validation":report["decision"],
            "brier_gain":report["best_candidate_brier_gain"],
            "feature_sha256":report["feature_sha256"],
            "source_truth_qualified":False,"live_ready":False,
        },sort_keys=True))
        return 0
    except (ReplayRefused,ValueError,OSError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc),
                          "live_ready":False}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
