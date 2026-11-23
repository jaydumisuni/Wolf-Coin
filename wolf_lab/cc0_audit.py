"""Private cross-source factual audit and already-exposed holdout uncertainty.

Never feeds Football-Data prices, match results or other restricted records
into neural training. The cross-source check verifies a CC0 fixture archive
against an independent privately held result file by match identity and score.
The holdout audit is post-freeze diagnostic; cannot re-select the model.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import csv
import numpy as np
import json

from .cc0_training import _team,load_cc0,featurize
from .cc0_pipeline import (
    PINNED_INPUTS,TRAINING_SEASONS,VALIDATION_SEASON,HISTORY_ONLY_SEASON,
    FINAL_SEASON,Model
)

# Aliases are ONLY for comparing two independent fixture archives.
AUDIT_TEAM_ALIASES={
    "brighton":"brighton & hove albion",
    "leeds":"leeds united",
    "leicester":"leicester city",
    "man united":"manchester united",
    "newcastle":"newcastle united",
    "tottenham":"tottenham hotspur",
    "ipswich":"ipswich town",
}


def normalize_for_comparison(name:str)->str:
    stem=_team(name)
    return AUDIT_TEAM_ALIASES.get(stem,stem)


def crosscheck_scores(cc0_file:Path,private_csv:Path,*,season:str,cc0_hash:str,csv_hash:str)->dict:
    cc0=load_cc0(cc0_file,season=season,sha256_expected=cc0_hash)
    raw=private_csv.read_bytes()
    if sha256(raw).hexdigest()!=csv_hash:raise ValueError("independent audit CSV digest mismatch")
    try:
        parsed=list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
        ref={}
        for row in parsed:
            key=(datetime.strptime(row["Date"],"%d/%m/%Y").date().isoformat(),
                 normalize_for_comparison(row["HomeTeam"]),
                 normalize_for_comparison(row["AwayTeam"]))
            if key in ref:raise ValueError("independent source duplicate fixture")
            ref[key]=(int(row["FTHG"]),int(row["FTAG"]))
    except (KeyError,ValueError,TypeError,UnicodeError,csv.Error) as e:
        raise ValueError("unqualified independent result source") from e
    first={fixture.key:(fixture.home_goals,fixture.away_goals) for fixture in cc0.fixtures}
    missing=sorted(set(first)-set(ref))
    other=sorted(set(ref)-set(first))
    conflicts=sorted([key for key in set(first)&set(ref) if first[key]!=ref[key]])
    return {
        "season":season,"cc0_sha256":cc0_hash,"audit_source_sha256":csv_hash,
        "cc0_count":len(first),"audit_count":len(ref),
        "matched_fixtures":len(set(first)&set(ref)),
        "missing_from_audit":len(missing),
        "missing_from_cc0":len(other),
        "score_conflicts":len(conflicts),
        "perfectly_reconciled":not (missing or other or conflicts),
    }


def diagnostic_holdout_audit(data:Path,record:dict,*,final_sha256:str,
                             bootstrap_iterations:int=5000,seed:int=1009)->dict:
    if bootstrap_iterations!=5000 or seed!=1009:
        raise ValueError("audit uses frozen bootstrap bounds")
    sources=[
       load_cc0(data/(name+"-en.1.json"),season=name,
                sha256_expected=PINNED_INPUTS[name],
                allow_missing=name==HISTORY_ONLY_SEASON)
       for name in (*TRAINING_SEASONS,VALIDATION_SEASON,HISTORY_ONLY_SEASON)
    ]
    sources.append(load_cc0(data/(FINAL_SEASON+"-en.1.json"),
                            season=FINAL_SEASON,sha256_expected=final_sha256,allow_missing=True))
    rows=featurize(sources)
    train=[r for part in rows[:len(TRAINING_SEASONS)] for r in part]
    observed=[r for r in rows[-1] if r.label is not None]
    if len(observed)<30:raise ValueError("insufficient holdout observations")
    if record["wolf_source_head"]!="170a555991910fd3db525c2070ace88568b6f0b4":
        raise ValueError("not the pre-frozen source generation")
    model=Model(**record["selected_model"])
    predicted=model.predict(observed)
    y=np.asarray([r.label for r in observed],dtype=np.int64)
    frequencies=np.bincount(np.array([r.label for r in train]),minlength=3)
    prior=(frequencies+1)/(len(train)+3)
    reference=np.tile(prior,(len(observed),1))
    onehot=np.eye(3)[y]
    model_squared=np.sum((predicted-onehot)**2,axis=1)
    prior_squared=np.sum((reference-onehot)**2,axis=1)
    delta=prior_squared-model_squared
    days=defaultdict(list)
    for index,row in enumerate(observed):
        days[row.key[0]].append(index)
    day_keys=sorted(days)
    rng=np.random.default_rng(seed)
    vals=[]
    for _ in range(bootstrap_iterations):
        keys=rng.choice(day_keys,size=len(day_keys),replace=True)
        ix=[i for day in keys for i in days[day]]
        vals.append(float(np.mean(delta[ix])))
    ci=np.quantile(vals,[0.025,0.975])
    return {
        "schema":"wolf.cc0-neural-holdout-audit.v1",
        "heldout_sha256":final_sha256,
        "frozen_model_digest":record["frozen_digest"],
        "pre_frozen_wolf_commit":record["wolf_source_head"],
        "count":len(observed),"distinct_match_days":len(day_keys),
        "model_brier":round(float(model_squared.mean()),9),
        "class_prior_brier":round(float(prior_squared.mean()),9),
        "model_minus_prior_brier":round(float(model_squared.mean()-prior_squared.mean()),9),
        "model_log_loss":round(float(-np.mean(np.log(predicted[np.arange(len(y)),y]))),9),
        "class_prior_log_loss":round(float(-np.mean(np.log(prior[y]))),9),
        "prior_probabilities":[round(float(x),9) for x in prior],
        "day_cluster_bootstrap_iterations":bootstrap_iterations,
        "bootstrap_seed":seed,
        "prior_minus_model_brier_95_percentile_interval":[round(float(x),9) for x in ci],
        "interval_excludes_zero":bool(ci[0]>0 or ci[1]<0),
        "model_selection_modified":False,
        "financial_edge_proven":False,
        "live_admission":False,
        "warning":"45 scored matches from a stale, partial archive; wide correlated-data bootstrap interval; no bookmaker comparison or earnings evidence.",
    }
