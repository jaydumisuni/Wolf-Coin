"""Read-only reconciliation of frozen model, result and market evidence.

This audits evidence coverage. It neither trains models nor places orders.
The source and paired reports are locally sealed diagnostics, not independently
authenticated results. A rescheduled quote is not silently matched to a result
on the original fixture day.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from math import isclose, isfinite
from pathlib import Path

from wolf_lab.forward_market import QuoteRefused, digest, frozen, immutable
from wolf_lab.forward_market_cli import _private, _state, _transport_attestations

GOAL_SHA="7811afbaa047ba0b18530f4edf94dacf14bea0e55369fbbcb103e4b64428b4c6"
GOAL_SCHEMA="wolf.cc0-goal-poisson-forecast.v1"
LABELS={"H":0,"D":1,"A":2}

def _sealed(path, field, schema):
    raw=path.read_bytes()
    if len(raw)>2_000_000:
        raise QuoteRefused("report exceeds evidence limit")
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise QuoteRefused("report must be an object")
    body=dict(obj)
    seal=body.pop(field,None)
    if obj.get("schema")!=schema or seal!=digest(body):
        raise QuoteRefused("report schema or seal mismatch")
    return obj

def _index(records, allowed=None):
    if not isinstance(records,list):
        raise QuoteRefused("record array required")
    index={}
    for row in records:
        identity=row["identity"]
        if identity in index or (allowed is not None and identity not in allowed):
            raise QuoteRefused("duplicate or foreign fixture identity")
        index[identity]=row
    return index

def _number_matches(a,b):
    return type(a) in (float,int) and isfinite(a) and isclose(a,b,abs_tol=2e-11,rel_tol=0)

def _brier(p,y):
    return sum((v-(i==y))**2 for i,v in enumerate(p))

def reconcile(mlp_path:Path,goal_path:Path,source_report:Path,paired_report:Path,evidence_dir:Path):
    mlp=frozen(mlp_path)
    if sha256(goal_path.read_bytes()).hexdigest()!=GOAL_SHA:
        raise QuoteRefused("pinned goal forecast bytes changed")
    goal=_sealed(goal_path,"seal_sha256",GOAL_SCHEMA)
    if goal["original_mlp_future_forecast_digest"]!=mlp["forecast_digest_sha256"]:
        raise QuoteRefused("goal forecast is not linked to original freeze")
    original=_index(mlp["records"])
    alternate=_index(goal["records"],original)
    if set(original)!=set(alternate) or goal["forecast_count"]!=len(original):
        raise QuoteRefused("forecast fixture universes differ")
    for key,row in alternate.items():
        if row["fixture_day"]!=original[key]["fixture_day"]:
            raise QuoteRefused("frozen fixture date differs")
    source=_sealed(source_report,"result_digest_sha256","wolf.prelive-future-source-scoring.v1")
    paired=_sealed(paired_report,"sha256","wolf.paired-prospective-result-v1")
    if (source["forecast_digest_sha256"]!=mlp["forecast_digest_sha256"]
        or paired["original_mlp_forecast_digest"]!=mlp["forecast_digest_sha256"]
        or paired["goal_poisson_forecast_digest"]!=goal["seal_sha256"]
        or source["new_source_sha256"]!=paired["results_source_sha256"]
        or source["capture_utc"]!=paired["capture_utc"]):
        raise QuoteRefused("reports refer to different forecast or result evidence")
    capture=datetime.fromisoformat(source["capture_utc"].replace("Z","+00:00"))
    if capture.tzinfo is None or capture.utcoffset().total_seconds()!=0 or capture>datetime.now(timezone.utc):
        raise QuoteRefused("invalid result capture time")
    result=_index(source["matches"],original)
    pairs=_index(paired["paired_records"],original)
    missing=source["rescheduled_or_missing"]
    if (not isinstance(missing,list) or len(set(missing))!=len(missing)
        or not set(missing)<=set(original) or set(missing)&set(result)):
        raise QuoteRefused("invalid missing or rescheduled identity set")
    pending=len(original)-len(result)-len(missing)
    if (set(pairs)!=set(result) or source["scored_count"]!=len(result)
        or paired["paired_outcomes"]!=len(result) or source["unscored_count"]!=pending
        or paired["pending_outcomes"]!=pending or source["rescheduled_or_missing_count"]!=len(missing)
        or paired["rescheduled_or_missing_outcomes"]!=len(missing)
        or source["forecast_count"]!=len(original) or paired["forecast_count"]!=len(original)):
        raise QuoteRefused("outcome coverage does not reconcile")
    for key,row in result.items():
        pair=pairs[key]
        if (row["outcome"] not in LABELS or row["outcome"]!=pair["settled_outcome"]
            or row["fixture_day"]!=original[key]["fixture_day"]
            or date.fromisoformat(row["fixture_day"])>=capture.date()
            or row["forecast_probabilities_1x2"]!=original[key]["probabilities_1x2"]):
            raise QuoteRefused("settlement report contradicts frozen fixture")
        y=LABELS[row["outcome"]]
        a=_brier(original[key]["probabilities_1x2"],y)
        b=_brier(alternate[key]["probabilities_1x2"],y)
        if not all((_number_matches(row["brier"],a),_number_matches(pair["original_mlp_brier"],a),
                    _number_matches(pair["frozen_goal_poisson_brier"],b),
                    _number_matches(pair["mlp_minus_goal_brier"],a-b))):
            raise QuoteRefused("paired report arithmetic mismatch")
    directory=_private(evidence_dir)
    ledger=_state(mlp,directory)
    attestations=_transport_attestations(directory,ledger)
    quoted={e["record"]["quote"]["fixture_identity"] for e in ledger.records}
    unchanged={e["record"]["quote"]["fixture_identity"] for e in ledger.records
               if not e["record"]["schedule_changed"]}
    rescheduled={e["record"]["quote"]["fixture_identity"] for e in ledger.records
                 if e["record"]["schedule_changed"]}
    report={
        "schema":"wolf.forward-evidence-reconciliation.v1",
        "forecast_count":len(original),
        "paired_outcomes":len(result),
        "pending_outcomes":pending,
        "missing_or_rescheduled_outcomes":len(missing),
        "market_quote_records":len(ledger.records),
        "fixtures_with_quote_evidence":len(quoted),
        "fixtures_without_quote_evidence":len(original)-len(quoted),
        "rescheduled_quote_fixtures":len(rescheduled),
        "same_original_date_quote_and_result_pairs":len(unchanged&set(result)),
        "rescheduled_quote_and_result_pairs_requiring_review":len(rescheduled&set(result)),
        "http_date_attestations_checked":attestations,
        "original_forecast_digest":mlp["forecast_digest_sha256"],
        "goal_forecast_digest":goal["seal_sha256"],
        "source_report_digest":source["result_digest_sha256"],
        "paired_report_digest":paired["sha256"],
        "market_journal_seal":ledger.snapshot()["seal_sha256"],
        "status":"AWAIT_FUTURE_OUTCOMES" if not result else "LOCAL_EVIDENCE_COVERAGE_RECONCILED",
        "independent_source_authentication_proven":False,
        "predictive_superiority_proven":False,
    }
    report["seal_sha256"]=digest(report)
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("mlp","goal","source-report","paired-report","evidence-dir","output"):
        parser.add_argument("--"+name, type=Path,required=True)
    args=parser.parse_args(argv)
    report=reconcile(args.mlp,args.goal,args.source_report,args.paired_report,args.evidence_dir)
    immutable(args.output,json.dumps(report,sort_keys=True,indent=2).encode()+b"\n")
    print(json.dumps(report,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
