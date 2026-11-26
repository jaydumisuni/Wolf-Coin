"""Prospective, account-free freeze of a previously trained Wolf CC0 model.

No research data are fetched. Dates/fixtures come from a pinned, previously
downloaded CC0 source. The model is frozen and never updated by this route.
Future evaluation requires outcomes acquired *after* this freeze.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from typing import Any

from wolf_lab.cc0_training import featurize, load_cc0
from wolf_lab.typed_tabular import (
    load_frozen, predict_independently, PINNED_INPUTS,
    TRAINING_SEASONS, VALIDATION_SEASON, HISTORY_ONLY_SEASON, FINAL_SEASON,
    EXPECTED_FINAL_SOURCE_SHA256, MODEL_FROZEN_FILE_SHA256,
    TypedRouteRefused,
)
from wolf_lab.prelive_feedback import _json, _sha, _write_new

SCHEMA="wolf.prelive-forward-freeze.v1"
AS_OF=date(2026,11,26)
MIN_FUTURE=50
RESEARCH_ONLY="NO_AUTHORIZED_PROVIDER_OR_FINANCIAL_ACTION"


def freeze(model_path:Path, data_root:Path, *, as_of:date=AS_OF)->dict:
    if as_of!=AS_OF:
        raise TypedRouteRefused("prospective cutoff frozen on 2026-11-26")
    model=load_frozen(model_path)
    seasons=[]
    names=(*TRAINING_SEASONS, VALIDATION_SEASON, HISTORY_ONLY_SEASON, FINAL_SEASON)
    for name in names:
        expected=EXPECTED_FINAL_SOURCE_SHA256 if name==FINAL_SEASON else PINNED_INPUTS[name]
        seasons.append(load_cc0(data_root/(name+"-en.1.json"),
                                season=name,sha256_expected=expected,
                                allow_missing=name in (HISTORY_ONLY_SEASON,FINAL_SEASON)))
    source=seasons[-1]
    if source.scored!=45 or source.unscored!=335:
        raise TypedRouteRefused("known previous snapshot coverage differs")
    future=[
        r for r in featurize(tuple(seasons))[-1]
        if r.label is None and date.fromisoformat(r.key[0])>as_of
    ]
    if len(future)<MIN_FUTURE or len({r.key for r in future})!=len(future):
        raise TypedRouteRefused("future fixture set too small or duplicated")
    records=[]
    for row in future:
        probs=predict_independently(model["selected_model"],row.features)
        records.append({
            "identity":"|".join(row.key),
            "fixture_day":row.key[0],
            "prior_only_features":[round(x,12) for x in row.features],
            "probabilities_1x2":[round(float(x),12) for x in probs],
            "result_known_at_freeze":False,
        })
    records.sort(key=lambda x:x["identity"])
    report={
        "schema":SCHEMA,
        "status":"FROZEN_PENDING_UNSEEN_FUTURE_OUTCOMES",
        "cutoff_date":as_of.isoformat(),
        "frozen_model_sha256":MODEL_FROZEN_FILE_SHA256,
        "fixture_snapshot_sha256":EXPECTED_FINAL_SOURCE_SHA256,
        "source_license":"CC0-1.0",
        "schedule_is_provisional":True,
        "snapshot_scored_at_freeze":source.scored,
        "snapshot_unscored_at_freeze":source.unscored,
        "future_match_count":len(records),
        "records":records,
        "market_odds_available":False,
        "real_account_used":False,
        "financial_edge_proven":False,
        "live_admission":False,
        "authority":RESEARCH_ONLY,
        "note":"Prior-only stale snapshot features; schedule changes and price/quote provenance must be handled separately. Already played fixtures on 2026-11-26 or earlier are excluded.",
    }
    report["forecast_digest_sha256"]=_sha(report)
    return report


def verify_freeze(report:dict)->bool:
    if (report.get("schema")!=SCHEMA or report.get("cutoff_date")!=AS_OF.isoformat()
        or report.get("frozen_model_sha256")!=MODEL_FROZEN_FILE_SHA256
        or report.get("fixture_snapshot_sha256")!=EXPECTED_FINAL_SOURCE_SHA256
        or report.get("authority")!=RESEARCH_ONLY
        or report.get("live_admission") is not False
        or report.get("financial_edge_proven") is not False
        or report.get("market_odds_available") is not False
        or report.get("status")!="FROZEN_PENDING_UNSEEN_FUTURE_OUTCOMES"):
        raise TypedRouteRefused("prospective model freeze contract changed")
    actual=report.get("forecast_digest_sha256")
    data={key:v for key,v in report.items() if key!="forecast_digest_sha256"}
    if _sha(data)!=actual:
        raise TypedRouteRefused("prospective forecast digest mismatch")
    records=report.get("records")
    if not isinstance(records,list) or len(records)!=report.get("future_match_count") or len(records)<MIN_FUTURE:
        raise TypedRouteRefused("future forecast count changed")
    seen=set()
    for entry in records:
        if set(entry)!={"identity","fixture_day","prior_only_features",
                       "probabilities_1x2","result_known_at_freeze"}:
            raise TypedRouteRefused("malformed future forecast")
        identity=entry["identity"]
        if identity in seen or identity.split("|")[0]!=entry["fixture_day"]:
            raise TypedRouteRefused("duplicate or malformed future identity")
        seen.add(identity)
        if date.fromisoformat(entry["fixture_day"])<=AS_OF:
            raise TypedRouteRefused("past fixture leaked into future forecast")
        probs=entry["probabilities_1x2"]
        if (not isinstance(probs,list) or len(probs)!=3 or
            any(type(x) is not float or not 0<x<1 for x in probs)
            or abs(sum(probs)-1)>2e-11
            or entry["result_known_at_freeze"] is not False):
            raise TypedRouteRefused("future prediction or outcome leakage")
    return True


def score_future_after_settlement(
    frozen: dict, results: dict, *, independent_results_source_sha256: str
)->dict:
    """Score later outcomes without touching model weights or the frozen file.

    A matching SHA asserts byte identity to caller-supplied future evidence;
    it does not independently authenticate an external results provider.
    No order, stake, quote or return is inferable from this interface.
    """
    verify_freeze(frozen)
    if (not isinstance(results,dict) or
        set(results)!={"schema","observed_day","outcomes"} or
        results["schema"]!="wolf.prelive-future-outcomes.v1"
        or type(independent_results_source_sha256) is not str
        or len(independent_results_source_sha256)!=64
        or any(c not in "0123456789abcdef" for c in independent_results_source_sha256)
    ):
        raise TypedRouteRefused("typed future result evidence required")
    observed=date.fromisoformat(results["observed_day"])
    if observed<=AS_OF:
        raise TypedRouteRefused("cannot observe prospective results on freeze day")
    labeled=results["outcomes"]
    if not isinstance(labeled,list) or not labeled:
        raise TypedRouteRefused("at least one future settled result required")
    ids={r["identity"]:r for r in frozen["records"]}
    used=set()
    proper=0.0
    for row in labeled:
        if not isinstance(row,dict) or set(row)!={"identity","outcome","settled_day"}:
            raise TypedRouteRefused("unrecognized future outcome schema")
        key=row["identity"]
        if key in used or key not in ids:
            raise TypedRouteRefused("duplicate or out-of-freeze future identity")
        used.add(key)
        day=date.fromisoformat(ids[key]["fixture_day"])
        confirmed=date.fromisoformat(row["settled_day"])
        if confirmed<=day or confirmed>observed:
            raise TypedRouteRefused("future outcome before fixture or after observation")
        actual=row["outcome"]
        if actual not in ("H","D","A"):
            raise TypedRouteRefused("unrecognized future class result")
        pred=ids[key]["probabilities_1x2"]
        proper+=sum((pred[i]-float(actual==o))**2
                    for i,o in enumerate(("H","D","A")))
    n=len(labeled)
    return {
        "schema":"wolf.prelive-future-score.v1",
        "status":"FUTURE_OUTCOME_DIAGNOSTIC_NOT_MARKET_EDGE",
        "forecast_sha256":frozen["forecast_digest_sha256"],
        "external_future_result_evidence_sha256":independent_results_source_sha256,
        "externally_authenticated_provider_settlement":False,
        "outcomes_scored":n,
        "remaining_frozen_predictions":len(ids)-n,
        "forecast_brier":proper/n,
        "market_baseline_pending":True,
        "market_price_evidence_pending":True,
        "profit_proven":False,
        "live_admission":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description="Freeze only future 1X2 probabilities, no funded account")
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--private-output-dir",type=Path,required=True)
    args=p.parse_args(argv)
    out=args.private_output_dir.resolve()
    if not out.is_dir() or out.is_symlink() or out.stat().st_mode & 0o077:
        raise TypedRouteRefused("owner-only output directory mode 0700 required")
    target=out/"forward-freeze-20261126.json"
    if target.exists():
        raise TypedRouteRefused("existing forecast immutable; no rewrite")
    report=freeze(args.model,args.data_root)
    verify_freeze(report)
    _write_new(target,_json(report))
    print(json.dumps({
        "status":report["status"],
        "future_matches":report["future_match_count"],
        "frozen_digest_sha256":report["forecast_digest_sha256"],
        "file_sha256":sha256(target.read_bytes()).hexdigest(),
        "market_edge_proven":False,
        "live_admission":False,
    },sort_keys=True))
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,ValueError,TypeError) as e:
        print(json.dumps({"status":"REFUSED","reason":str(e),"live_admission":False}),
              file=sys.stderr)
        sys.exit(2)
