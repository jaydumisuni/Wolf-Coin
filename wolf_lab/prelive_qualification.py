"""Pre-live, source-bound, four-season sequential loss-feedback qualification.

Predeclared protocol, not a hyperparameter search. Future scores are never
passed to forecast or fit. Private bookmaker quotes are used for EVALUATION
ONLY and never influence model fitting, calibrator updates or selection.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
import argparse
import csv
import json

import numpy as np

from wolf_lab.cc0_audit import normalize_for_comparison
from wolf_lab.cc0_mlp import fit, proper
from wolf_lab.cc0_pipeline import PINNED_INPUTS, CC0_LICENSE_SHA256
from wolf_lab.cc0_training import load_cc0, featurize
from wolf_lab.loss_feedback import (
    FeedbackError, Forecast, Settlement, LossLearner, write_immutable, _digest,
)

SCHEMA="wolf.prelive-loss-qualification.v1"
TRAIN=("2017-18","2018-19","2019-20","2020-21")
EVALUATE=("2021-22","2022-23","2023-24","2024-25")
CSV_NAMES={"2022-23":"E0-2223.csv","2023-24":"E0-2324.csv",
           "2024-25":"E0-2425.csv"}
MARKET_HASH={
"2022-23":"8442792d3b614c94ea3cf381bd2736805889cc1713169035368fff19c3d02380",
"2023-24":"b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3",
"2024-25":"d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4",
}
METHOD="fixed 8-unit MLP trained once on 2017/18–2020/21; 0.04 online cross-entropy bias correction after settlement"
BOOTSTRAP_ITERATIONS=2000
BOOTSTRAP_SEED=20261126
MIN_BRIER_GAIN=0.005
_MIN_LOG_GAIN=0.005


def _market_team(name:str)->str:
    # Cross-archive identity comparison only; no restricted data train features.
    val=normalize_for_comparison(name)
    return {"luton":"luton town"}.get(val,val)


def _market_eval_only(path:Path,digest:str,examples)->tuple[np.ndarray,dict]:
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=digest:
        raise FeedbackError("private market comparison source digest mismatch")
    try:
        parsed=list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
        reference={}
        for row in parsed:
            d=date.strptime(row["Date"], "%d/%m/%Y") if hasattr(date,"strptime") else __import__("datetime").datetime.strptime(row["Date"], "%d/%m/%Y").date()
            key=(d.isoformat(),_market_team(row["HomeTeam"]),_market_team(row["AwayTeam"]))
            odds=tuple(float(row[k]) for k in ("B365H","B365D","B365A"))
            if any(not np.isfinite(x) or x<=1.0 or x>=1000 for x in odds):
                raise FeedbackError("invalid market quote")
            label={"H":0,"D":1,"A":2}[row["FTR"]]
            if key in reference:
                raise FeedbackError("duplicate market fixture")
            reference[key]=(odds,label)
    except (ValueError,KeyError,UnicodeError,TypeError,csv.Error) as exc:
        raise FeedbackError("invalid private market evaluation source") from exc
    expected_keys={(r.key[0],_market_team(r.key[1]),_market_team(r.key[2])) for r in examples}
    if len(expected_keys)!=len(examples) or set(reference)!=expected_keys:
        raise FeedbackError("market/CC0 fixture identity mismatch")
    out=[]
    for r in examples:
        odds,label=reference[(r.key[0],_market_team(r.key[1]),_market_team(r.key[2]))]
        if r.label!=label:
            raise FeedbackError("market/CC0 result conflict")
        inv=np.asarray([1/x for x in odds],dtype=np.float64)
        out.append(inv/inv.sum())
    return np.asarray(out),{"source_sha256":digest,"matched_fixtures":len(out),
                            "usage":"private quote-based SCORE COMPARISON ONLY; never trained"}


def _mean_score(labels:list[int],probs)->dict:
    return proper(np.asarray(labels,dtype=np.int64),np.asarray(probs,dtype=np.float64))


def _per_match_brier(labels,prob):
    p=np.asarray(prob,dtype=np.float64)
    targets=np.eye(3,dtype=np.float64)[np.asarray(labels,dtype=np.int64)]
    return np.sum((p-targets)**2,axis=1)


def _bootstrap_by_day(days,delta,seed=BOOTSTRAP_SEED)->tuple[float,float]:
    groups=defaultdict(list)
    for i,d in enumerate(days):
        groups[d].append(float(delta[i]))
    unique=sorted(groups)
    if len(unique)<80:
        raise FeedbackError("too few independent match-day clusters")
    data=[(sum(groups[k]),len(groups[k])) for k in unique]
    rng=np.random.default_rng(seed)
    draws=rng.integers(0,len(data),size=(BOOTSTRAP_ITERATIONS,len(data)))
    arr=np.asarray(data,dtype=np.float64)
    totals=arr[draws]
    means=totals[:,:,0].sum(axis=1)/totals[:,:,1].sum(axis=1)
    q=np.quantile(means,[0.025,0.975])
    return float(q[0]),float(q[1])


def qualify(cc0_folder:Path,market_folder:Path,*,archive:Path|None=None)->dict:
    license_bytes=(cc0_folder/"CC0-LICENSE.md").read_bytes()
    if sha256(license_bytes).hexdigest()!=CC0_LICENSE_SHA256:
        raise FeedbackError("CC0 training license hash mismatch")
    sources=[load_cc0(cc0_folder/(s+"-en.1.json"),
                      season=s,sha256_expected=PINNED_INPUTS[s]) for s in (*TRAIN,*EVALUATE)]
    partitions=featurize(sources)
    training=tuple(r for group in partitions[:len(TRAIN)] for r in group)
    if len(training)!=1520 or any(r.label is None for r in training):
        raise FeedbackError("unexpected historical training coverage")
    model=fit(training,"mlp")  # Frozen before evaluations; NO tuning on outcomes.
    frozen_model_sha256=_digest({"architecture":"mlp","parameters":asdict_model(model)})
    counts=np.bincount(np.asarray([r.label for r in training]),minlength=3)
    prior=(counts+1)/(len(training)+3)
    folds=[]
    comparison_days=[]
    market_delta=[]
    frozen_delta=[]
    records=[]
    loss_receipts=0
    replay_ok=True
    private_archive=[]
    for season,examples in zip(EVALUATE,partitions[len(TRAIN):]):
        if len(examples)!=380 or any(r.label is None for r in examples):
            raise FeedbackError("incomplete evaluation season")
        learner=LossLearner()
        by_day=defaultdict(list)
        for example in examples:
            by_day[example.key[0]].append(example)
        labels=[];adaptive=[];frozen=[];days=[];priors=[]
        local_losses=0
        for day,rows in sorted(by_day.items()):
            # Model receives sanitized feature-only views; no settled label.
            sealed_features=[replace(row,label=None) for row in rows]
            base_forecasts=model.predict(sealed_features)
            all_forecasts=[]
            for index,row in enumerate(rows):
                base=tuple(float(x) for x in base_forecasts[index])
                adjusted=learner.predict(base)
                event_id=sha256((season+"|"+str(row.key)).encode()).hexdigest()
                item=Forecast("pred:"+event_id,
                              "match:"+event_id,
                              day+"T08:00:00Z",adjusted,
                              int(np.argmax(adjusted)),
                              frozen_model_sha256,learner.version)
                learner.register(item)
                all_forecasts.append((item,row))
                labels.append(int(row.label))
                adaptive.append(adjusted)
                frozen.append(base)
                days.append(season+"|"+day)
                priors.append(tuple(float(x) for x in prior))
            # Delayed update: all daily forecasts are committed BEFORE any
            # outcome from that match-day is allowed into the calibrator.
            for item,row in all_forecasts:
                settled=Settlement("settle:"+item.prediction_id[5:],
                                   item.prediction_id,
                                   day+"T23:59:59Z",int(row.label),
                                   frozen_model_sha256,1.0,2.0)
                result=learner.settle(settled)
                if result["virtual_pnl"]<0:
                    local_losses+=1
                if result["learning_version"]!=learner.version:
                    raise FeedbackError("learning version not advanced")
        if learner.version!=len(examples):
            raise FeedbackError("missing settled forecasts")
        # Distinct process-load equivalent: rederive every parameter from
        # immutable forecast/receipt events, reject any tampering.
        recovered=LossLearner.from_snapshot(learner.snapshot())
        if recovered.snapshot()!=learner.snapshot():
            replay_ok=False
            raise FeedbackError("restart replay changed learned weights")
        result={"season":season,"fixtures":len(labels),
                "match_days":len(by_day),
                "forecast_settlements":learner.version,
                "synthetic_winning_receipts":len(labels)-local_losses,
                "synthetic_losing_receipts":local_losses,
                "market":None,
                "adaptive":_mean_score(labels,adaptive),
                "frozen":_mean_score(labels,frozen),
                "historical_class_prior":_mean_score(labels,priors),
                "bias_end":[round(x,9) for x in learner.bias],
                "sealed_journal_sha256":learner.snapshot()["seal_sha256"]}
        loss_receipts+=local_losses
        frozen_delta.extend((_per_match_brier(labels,frozen)-_per_match_brier(labels,adaptive)).tolist())
        if season in CSV_NAMES:
            market,source=_market_eval_only(market_folder/CSV_NAMES[season],MARKET_HASH[season],examples)
            market_score=_mean_score(labels,market)
            delta=_per_match_brier(labels,market)-_per_match_brier(labels,adaptive)
            market_delta.extend(delta.tolist())
            comparison_days.extend(days)
            result["market"]=market_score
            result["market_source"]=source
            result["market_minus_adaptive_brier"]=round(market_score["brier"]-result["adaptive"]["brier"],9)
            result["adaptive_better_than_market_by_at_least_0_005"]=(
                market_score["brier"]-result["adaptive"]["brier"]>=MIN_BRIER_GAIN
                and market_score["log_loss"]-result["adaptive"]["log_loss"]>=_MIN_LOG_GAIN)
        folds.append(result)
        if archive is not None:
            name=archive/("journal-"+season+".json")
            written=write_immutable(name,learner.snapshot())
            private_archive.append({"season":season,"file":name.name,"file_sha256":written})
    all_days=[s+"|"+r.key[0] for s,part in zip(EVALUATE,partitions[len(TRAIN):]) for r in part]
    frozen_ci=_bootstrap_by_day(all_days,frozen_delta,seed=BOOTSTRAP_SEED)
    market_ci=_bootstrap_by_day(comparison_days,market_delta,seed=BOOTSTRAP_SEED+1)
    market_folds=[x for x in folds if x["market"] is not None]
    market_consistent=(len(market_folds)==3 and
                       all(x["adaptive_better_than_market_by_at_least_0_005"] for x in market_folds)
                       and market_ci[0] > 0.0)
    fixed_consistent=(all(x["frozen"]["brier"]-x["adaptive"]["brier"]>=MIN_BRIER_GAIN
                          and x["frozen"]["log_loss"]-x["adaptive"]["log_loss"]>=_MIN_LOG_GAIN
                          for x in folds) and frozen_ci[0]>0.0)
    result={
      "schema":SCHEMA,
      "protocol":"FROZEN_BEFORE_QUALIFICATION_V1",
      "mode":"HISTORICAL_OFFLINE_ONLY",
      "method":METHOD,
      "source_rights":"CC0-1.0 outcomes train; separate private bookmaker odds evaluation ONLY",
      "trainer_inputs_sha256":{x:PINNED_INPUTS[x] for x in TRAIN},
      "evaluation_inputs_sha256":{x:PINNED_INPUTS[x] for x in EVALUATE},
      "frozen_model_sha256":frozen_model_sha256,
      "train_fixtures":len(training),
      "evaluation_fixtures":sum(x["fixtures"] for x in folds),
      "total_settled_learning_events":sum(x["forecast_settlements"] for x in folds),
      "settled_synthetic_losses":loss_receipts,
      "seasons":folds,
      "paired_cluster_bootstrap":{
        "method":"calendar-match-day clusters, with replacement",
        "iterations":BOOTSTRAP_ITERATIONS,"seed":BOOTSTRAP_SEED,
        "frozen_minus_adaptive_brier_ci95":[round(x,9) for x in frozen_ci],
        "market_minus_adaptive_brier_ci95":[round(x,9) for x in market_ci],
        "pooled_frozen_minus_adaptive_gain":round(float(np.mean(frozen_delta)),9),
        "pooled_market_minus_adaptive_gain":round(float(np.mean(market_delta)),9),
        "market_qualified_folds":len(market_folds),
      },
      "historical_consistent_market_advantage":market_consistent,
      "historical_consistent_frozen_model_advantage":fixed_consistent,
      "learning_settlement_and_restart_mechanism_verified":replay_ok and loss_receipts>0,
      "repeated_predictive_superiority_gate_passed":market_consistent and fixed_consistent,
      "source_windows_already_inspected":True,
      "independent_future_unseen_holdout_evaluated":False,
      "predictive_superiority_independently_proven":False,
      "real_account_losses_integrated":False,
      "production_autonomous_retraining_enabled":False,
      "real_money_profit_proven":False,
      "no_funds_or_provider_connections":True,
      "no_strategy_release_authority":True,
      "private_journals":private_archive,
      "verdict":"RESEARCH_ONLY_NO_LIVE_EDGE_ADMISSION",
    }
    result["seal_sha256"]=_digest(result)
    return result


def asdict_model(model):
    from dataclasses import asdict
    return asdict(model)


def main(argv=None):
    parser=argparse.ArgumentParser(prog="wolf-prelive-qualify")
    parser.add_argument("--cc0-dir",type=Path,required=True)
    parser.add_argument("--market-audit-dir",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    # Output dir must already exist, be owned by caller, and be private.
    out=args.output_dir.resolve()
    if not out.is_dir() or out.stat().st_mode&0o077:
        parser.error("existing private owner-only output directory required")
    try:
        report=qualify(args.cc0_dir,args.market_audit_dir,archive=out)
        digest=write_immutable(out/"qualification.json",report)
    except (FeedbackError,ValueError,OSError,TypeError,KeyError) as exc:
        parser.exit(2,"PREFLIGHT_OR_REPLAY_REFUSED: "+str(exc)+"\n")
    print(json.dumps({
      "status":report["verdict"],"trained":report["train_fixtures"],
      "evaluated":report["evaluation_fixtures"],
      "settled":report["total_settled_learning_events"],
      "learning_verified":report["learning_settlement_and_restart_mechanism_verified"],
      "market_consistent":report["historical_consistent_market_advantage"],
      "predictive_superiority_independently_proven":False,
      "live_admission":False,
      "report_sha256":digest},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
