"""Target-owned typed tabular inference adapter for Formula/SUP review.

Builds a replayable, self-contained candidate-only prediction envelope from
the already-frozen CC0 numeric MLP. The independent verifier is *stdlib-only*
and implements tanh+softmax numerically without importing NumPy or the training
model. Neither side grants Formula mathematical authority or SUP execution.

This is a typed integration candidate, NOT a newly unexamined holdout, a
qualified Soup/SUP-Bit training method, or a betting execution interface.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from math import exp, isfinite, tanh
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

from wolf_lab.cc0_training import CC0SourceError, FEATURES, featurize, load_cc0
# Independent verifier re-declares exact historical freeze contract instead
# of importing cc0_pipeline (which imports the NumPy training implementation).
# Deliberate independent source-bound constants; negative tests detect drift.
SOURCE_REV = 'e6744429ee395bc86f247348c6184bb08d4eb361'
CC0_LICENSE_SHA256 = '36ffd9dc085d529a7e60e1276d73ae5a030b020313e6c5408593a6ae2af39673'
FROZEN_SCHEMA = 'wolf.cc0-frozen-mlp-evidence.v1'
TRAINING_SEASONS = ('2017-18', '2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24')
VALIDATION_SEASON = '2024-25'
HISTORY_ONLY_SEASON = '2025-26'
FINAL_SEASON = '2026-27'
PINNED_INPUTS = {'2017-18': 'b635f2442a94aa91d85f282fc5e8f7f5dc4f0d04e3e30c4472102f5708d7548c', '2018-19': 'e2224d86f0605a5a1b5b019c845cdecb13aca1d88035686d4159b875250d4730', '2019-20': '9e1695f85ce5553f762e809dea357ec0a95838939be89569060a83c4e98a302d', '2020-21': '21ddf26b48469da530c51ccc4857bf1a534bda3aed08766b55185efb142e9a20', '2021-22': 'fbdfd426fa18fa2f8630b77de87c082734da495ac4668d6d72f29f76b73b9564', '2022-23': '8d09f0f9846981626cdfec48903e1f21e7c79aabe6f92535c9e092e8e79b808b', '2023-24': '03e13eafbf78dfe00d7e89dd3bf6643986eb6e8fd86c7664aeb8c5bc0bed88d0', '2024-25': 'c3d18f552d83382cd4b6b21127adbbfe38e7f8618ddc979fb5404f2df07d0a75', '2025-26': 'd6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1'}

MODEL_FROZEN_SOURCE = "170a555991910fd3db525c2070ace88568b6f0b4"
MODEL_FROZEN_DIGEST = "sha256:9b0e22f38810950b5920d4ff52ff6c2dbf96691c7e414946dd0e4f9452e48ef7"
MODEL_FROZEN_FILE_SHA256 = "2eb587952d5fb72dd25fcaa50aac9b46d6c4e6d3be33a02b502bb7e5a09a3fba"
EXPECTED_FINAL_SOURCE_SHA256 = "bb91f0ab3e8359df163bb9ec98549bfed85e200dd4c32f3bd606b5890d932dd2"
SCHEMA = "wolf.typed-tabular-1x2-candidate.v1"
MAX_ROWS = 500
MAX_FILE_BYTES = 300_000
MAX_ABS_PARAMETER = 10_000.0
PREDICTION_DECIMALS = 12
PREDICTION_TOLERANCE = 3e-12


class TypedRouteRefused(ValueError):
    pass


def digest(data: Any) -> str:
    return sha256(json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()


def _read_json(path: Path, max_bytes: int=MAX_FILE_BYTES) -> dict:
    p = Path(path)
    if not p.is_file() or p.stat().st_size <= 2 or p.stat().st_size > max_bytes:
        raise TypedRouteRefused("JSON evidence file missing or oversized")
    try:
        obj=json.loads(p.read_text(encoding="utf-8"))
    except (ValueError,UnicodeError,OSError) as e:
        raise TypedRouteRefused("unreadable JSON evidence") from e
    if not isinstance(obj,dict):
        raise TypedRouteRefused("JSON evidence must be a mapping")
    return obj


def _number(x: Any) -> float:
    if type(x) not in (int,float) or not isfinite(x) or abs(x)>MAX_ABS_PARAMETER:
        raise TypedRouteRefused("nonfinite or oversized model parameter")
    return float(x)


def _vector(raw: Any, expected: int, *, positive: bool=False) -> tuple[float,...]:
    if not isinstance(raw,(tuple,list)) or len(raw)!=expected:
        raise TypedRouteRefused("model vector dimension mismatch")
    val=tuple(_number(x) for x in raw)
    if positive and any(x<=0 for x in val):
        raise TypedRouteRefused("model scale must be positive")
    return val


def _matrix(raw: Any, height: int, width: int)->tuple[tuple[float,...],...]:
    if not isinstance(raw,(tuple,list)) or len(raw)!=height:
        raise TypedRouteRefused("model matrix row count mismatch")
    return tuple(_vector(row,width) for row in raw)


def _validated_weights(model: Any) -> dict:
    if not isinstance(model,dict) or set(model)!={"kind","a","b","c","d","mean","scale"}:
        raise TypedRouteRefused("unexpected model structure")
    if model["kind"]!="mlp":
        raise TypedRouteRefused("only frozen eight-unit MLP is supported")
    size=len(FEATURES)
    params={
        "mean":_vector(model["mean"],size),
        "scale":_vector(model["scale"],size,positive=True),
        "a":_matrix(model["a"],size,8),
        "b":_vector(model["b"],8),
        "c":_matrix(model["c"],8,3),
        "d":_vector(model["d"],3),
    }
    return params


def load_frozen(frozen_path:Path)->dict:
    raw=Path(frozen_path).read_bytes()
    if sha256(raw).hexdigest()!=MODEL_FROZEN_FILE_SHA256:
        raise TypedRouteRefused("frozen model file bytes do not match independently pinned digest")
    model=_read_json(frozen_path)
    if (model.get("schema")!=FROZEN_SCHEMA
        or model.get("wolf_source_head")!=MODEL_FROZEN_SOURCE
        or model.get("frozen_digest")!=MODEL_FROZEN_DIGEST
        or model.get("upstream_sha")!=SOURCE_REV
        or model.get("license")!="CC0-1.0"
        or model.get("license_sha256")!=CC0_LICENSE_SHA256
        or model.get("dataset_sha256")!={s:PINNED_INPUTS[s] for s in (*TRAINING_SEASONS,VALIDATION_SEASON)}
        or model.get("future_test_dataset_not_loaded") is not True
        or model.get("financial_edge_proven") is not False
        or model.get("live_enabled") is not False
        or model.get("sup_training_authorized") is not False
        or model.get("selection",{}).get("selected_kind")!="mlp"):
        raise TypedRouteRefused("frozen model source, license or safety flags mismatch")
    _validated_weights(model.get("selected_model"))
    return model


def prior_only_rows(data_root:Path):
    """Reconstruct already-examined 2026/27 features without future labels."""
    sources=[]
    for season in (*TRAINING_SEASONS,VALIDATION_SEASON,HISTORY_ONLY_SEASON,FINAL_SEASON):
        expected=(EXPECTED_FINAL_SOURCE_SHA256 if season==FINAL_SEASON else PINNED_INPUTS[season])
        sources.append(load_cc0(Path(data_root)/(season+"-en.1.json"),
                               season=season,sha256_expected=expected,
                               allow_missing=season in (HISTORY_ONLY_SEASON,FINAL_SEASON)))
    final=sources[-1]
    if final.scored!=45 or final.unscored!=335:
        raise TypedRouteRefused("first frozen final snapshot coverage changed")
    return tuple(row for row in featurize(tuple(sources))[-1] if row.label is not None)


def predict_independently(model:Mapping[str,Any],features: Sequence[float])->tuple[float,float,float]:
    """Pure-Python independent numerical implementation, no NumPy."""
    p=_validated_weights(model)
    x=_vector(features,len(FEATURES))
    z=[(x[j]-p["mean"][j])/p["scale"][j] for j in range(len(x))]
    hidden=[tanh(sum(z[j]*p["a"][j][k] for j in range(len(z)))+p["b"][k])
            for k in range(8)]
    logits=[sum(hidden[k]*p["c"][k][j] for k in range(8))+p["d"][j]
            for j in range(3)]
    maximum=max(logits)
    exponentials=[exp(x-maximum) for x in logits]
    total=sum(exponentials)
    if total<=0 or not isfinite(total):
        raise TypedRouteRefused("normalization failed")
    prob=tuple(x/total for x in exponentials)
    if not all(0<x<1 and isfinite(x) for x in prob):
        raise TypedRouteRefused("invalid predicted distribution")
    return prob


def build(frozen_path:Path,data_root:Path)->dict:
    """Offline candidate. Source freeze and subset already examined; no training."""
    frozen=load_frozen(frozen_path)
    rows=prior_only_rows(data_root)
    # Training implementation is used ONLY by the producer to establish parity.
    # Independent verifier below does not import or consult that model.
    from wolf_lab.cc0_mlp import Model
    reference=Model(**frozen["selected_model"])
    vectors=reference.predict(rows)
    all_rows=[]
    for row,prediction in zip(rows,vectors):
        pure=predict_independently(frozen["selected_model"],row.features)
        if any(abs(float(a)-b)>PREDICTION_TOLERANCE for a,b in zip(prediction,pure)):
            raise TypedRouteRefused("independent numerical verifier contradicts vectorized inference")
        all_rows.append({
            "id":"|".join(row.key),
            "prior_day_features":[round(x,PREDICTION_DECIMALS) for x in row.features],
            "class_probabilities":[round(float(x),PREDICTION_DECIMALS) for x in prediction],
        })
    candidate={
        "schema":SCHEMA,
        "status":"TARGET_OWNED_CANDIDATE_ONLY",
        "target_product":"Wolf-Coin",
        "architecture":"MLP:10x8:tanh:8x3:softmax",
        "feature_count":len(FEATURES),
        "feature_names":list(FEATURES),
        "classes":["H","D","A"],
        "model_source_head":MODEL_FROZEN_SOURCE,
        "model_file_sha256":MODEL_FROZEN_FILE_SHA256,
        "model_frozen_digest":MODEL_FROZEN_DIGEST,
        "historical_cc0_upstream_commit":SOURCE_REV,
        "dataset_license":"CC0-1.0",
        "evaluated_season":FINAL_SEASON,
        "evaluated_sha256":EXPECTED_FINAL_SOURCE_SHA256,
        "evaluated_scored_count":len(rows),
        "predictions":all_rows,
        "method_ownership":"Wolf-Coin numeric CPU; not SUP/Soup/SUP-Bit runtime",
        "formula_review_only":True,
        "sup_sim_route_qualified":False,
        "independent_formula_mathematical_certificate":False,
        "trained_against_new_2026_27_evidence":False,
        "financial_edge_proven":False,
        "execution_authority":False,
        "live_admission":False,
    }
    candidate["candidate_digest"]="sha256:"+digest(candidate)
    return candidate


def verify(candidate:Mapping[str,Any],frozen_path:Path,data_root:Path)->dict:
    if not isinstance(candidate,dict) or candidate.get("schema")!=SCHEMA:
        raise TypedRouteRefused("candidate schema mismatch")
    permitted_root={
        "schema","status","target_product","architecture","feature_count",
        "feature_names","classes","model_source_head","model_file_sha256",
        "model_frozen_digest","historical_cc0_upstream_commit","dataset_license",
        "evaluated_season","evaluated_sha256","evaluated_scored_count",
        "predictions","method_ownership","formula_review_only",
        "sup_sim_route_qualified","independent_formula_mathematical_certificate",
        "trained_against_new_2026_27_evidence","financial_edge_proven",
        "execution_authority","live_admission","candidate_digest",
    }
    if set(candidate)!=permitted_root:
        raise TypedRouteRefused("unrecognized candidate fields or missing safety controls")
    if not isinstance(candidate.get("candidate_digest"),str):
        raise TypedRouteRefused("missing candidate content seal")
    copy=dict(candidate)
    claimed=copy.pop("candidate_digest")
    if claimed!="sha256:"+digest(copy):
        raise TypedRouteRefused("candidate digest mismatch")
    for key,expected in (
        ("status","TARGET_OWNED_CANDIDATE_ONLY"),
        ("target_product","Wolf-Coin"),
        ("architecture","MLP:10x8:tanh:8x3:softmax"),
        ("feature_count",len(FEATURES)),
        ("feature_names",list(FEATURES)),
        ("classes",["H","D","A"]),
        ("model_source_head",MODEL_FROZEN_SOURCE),
        ("model_file_sha256",MODEL_FROZEN_FILE_SHA256),
        ("model_frozen_digest",MODEL_FROZEN_DIGEST),
        ("historical_cc0_upstream_commit",SOURCE_REV),
        ("dataset_license","CC0-1.0"),
        ("evaluated_season",FINAL_SEASON),
        ("evaluated_sha256",EXPECTED_FINAL_SOURCE_SHA256),
        ("method_ownership","Wolf-Coin numeric CPU; not SUP/Soup/SUP-Bit runtime"),
    ):
        if candidate.get(key)!=expected:
            raise TypedRouteRefused(f"candidate identity mismatch: {key}")
    for key,expected in (
        ("formula_review_only",True),
        ("sup_sim_route_qualified",False),
        ("independent_formula_mathematical_certificate",False),
        ("trained_against_new_2026_27_evidence",False),
        ("financial_edge_proven",False),
        ("execution_authority",False),
        ("live_admission",False),
    ):
        if candidate.get(key) is not expected:
            raise TypedRouteRefused("candidate attempts to claim unauthorized authority")
    frozen=load_frozen(frozen_path)
    rows=prior_only_rows(data_root)
    predictions=candidate.get("predictions")
    if not isinstance(predictions,list) or len(predictions)!=len(rows) or not 30<=len(predictions)<=MAX_ROWS:
        raise TypedRouteRefused("candidate row count inconsistent with pinned source")
    if candidate.get("evaluated_scored_count")!=len(rows):
        raise TypedRouteRefused("candidate coverage inconsistent")
    max_delta=0.0
    for record,row in zip(predictions,rows):
        if not isinstance(record,dict) or set(record)!={"id","prior_day_features","class_probabilities"}:
            raise TypedRouteRefused("prediction record malformed")
        if record["id"]!="|".join(row.key):
            raise TypedRouteRefused("prediction fixture out of order or invented")
        features=_vector(record["prior_day_features"],len(FEATURES))
        if any(abs(x-y)>1e-11 for x,y in zip(features,row.features)):
            raise TypedRouteRefused("candidate features diverge from prior-date source")
        declared=_vector(record["class_probabilities"],3,positive=True)
        independent=predict_independently(frozen["selected_model"],features)
        delta=max(abs(a-b) for a,b in zip(declared,independent))
        if delta>PREDICTION_TOLERANCE:
            raise TypedRouteRefused("candidate probabilities failed independent pure-Python replay")
        max_delta=max(max_delta,delta)
    return {
        "schema":"wolf.typed-tabular-independent-verification.v1",
        "candidate_digest":claimed,
        "model_frozen_digest":MODEL_FROZEN_DIGEST,
        "evaluated_rows":len(rows),
        "max_abs_probability_error":max_delta,
        "independent_implementation":"stdlib math.tanh and math.exp; no training engine, no NumPy",
        "status":"NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY",
        "formula_mathematical_authority":False,
        "sup_method_admitted":False,
        "neural_training_executed":False,
        "funding_ready":False,
        "live_admission":False,
    }


def replay_training(frozen_path:Path,data_root:Path)->dict:
    """Replay the original product-owned trainer on preholdout CC0 only.

    Research NumPy required here. Final 2026/27 and history-only 2025/26
    are not loaded or passed to training, even for features.
    """
    import time
    from dataclasses import asdict
    from wolf_lab.cc0_mlp import validated_comparison,selected_model

    frozen=load_frozen(frozen_path)
    seasons=(*TRAINING_SEASONS,VALIDATION_SEASON)
    sources=[
        load_cc0(Path(data_root)/(season+"-en.1.json"),
                 season=season,sha256_expected=PINNED_INPUTS[season])
        for season in seasons
    ]
    parts=featurize(sources)
    training=tuple(row for part in parts[:-1] for row in part)
    validation=parts[-1]
    if len(training)!=2660 or len(validation)!=380:
        raise TypedRouteRefused("original source training partition changed")
    start=time.perf_counter()
    decision=validated_comparison(training,validation)
    model=selected_model(training,decision)
    elapsed=time.perf_counter()-start
    if model is None:
        raise TypedRouteRefused("predeclared research selection now rejects original model")
    model_source=json.loads(json.dumps(asdict(model),allow_nan=False))
    if model_source!=frozen["selected_model"]:
        raise TypedRouteRefused("independent source training did not reproduce frozen weights")
    if decision!=frozen["selection"]:
        raise TypedRouteRefused("replayed training selection/validation differs from freeze")
    try:
        import resource
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        peak_rss_kib=None
    return {
        "schema":"wolf.typed-tabular-source-training-replay.v1",
        "status":"PRODUCT_OWNED_CPU_TRAINING_REPRODUCED",
        "model_file_sha256":MODEL_FROZEN_FILE_SHA256,
        "frozen_model_digest":MODEL_FROZEN_DIGEST,
        "train_seasons":list(TRAINING_SEASONS),
        "train_rows":len(training),
        "validation_season":VALIDATION_SEASON,
        "validation_rows":len(validation),
        "training_input_hashes":{season:PINNED_INPUTS[season] for season in seasons},
        "selected_model_kind":decision["selected_kind"],
        "selection_decision":decision["decision"],
        "replayed_model_sha256":digest(model_source),
        "reference_model_sha256":digest(frozen["selected_model"]),
        "replayed_selection_sha256":digest(decision),
        "reference_selection_sha256":digest(frozen["selection"]),
        "elapsed_seconds_this_host":round(elapsed,6),
        "process_peak_rss_kib_this_host":peak_rss_kib,
        "new_future_data_loaded":False,
        "supplemental_2025_26_data_loaded":False,
        "no_market_odds_training":True,
        "independent_training_algorithm":False,
        "sup_or_soup_method_approved":False,
        "formula_mathematical_authority":False,
        "sup_training_lease":False,
        "financial_edge_proven":False,
        "live_admission":False,
    }


def _write_new(path:Path, obj:dict)->None:
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def main(argv:Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="wolf-tabular",description="Offline typed model candidate and independent numerical replay")
    subs=p.add_subparsers(dest="action",required=True)
    for name in ("build","verify","retrain-proof"):
        sub=subs.add_parser(name)
        sub.add_argument("--frozen",required=True,type=Path)
        sub.add_argument("--data-root",required=True,type=Path)
        sub.add_argument("--output",required=True,type=Path)
        if name=="verify":
            sub.add_argument("--candidate",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        if args.action=="build":
            result=build(args.frozen,args.data_root)
        elif args.action=="verify":
            result=verify(_read_json(args.candidate,max_bytes=2_000_000),
                          args.frozen,args.data_root)
        else:
            result=replay_training(args.frozen,args.data_root)
        _write_new(args.output,result)
        print(json.dumps({"status":result["status"],"funding_ready":False,
                          "output":str(args.output)},sort_keys=True))
        return 0
    except (TypedRouteRefused,CC0SourceError,ValueError,TypeError,KeyError,OSError) as e:
        print(json.dumps({"status":"BLOCKED","reason":str(e),
                          "funding_ready":False}),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
