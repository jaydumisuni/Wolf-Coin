"""Pinned, offline CC0 neural-model freeze and later score-only evaluation.

No bookmaker data involved. Fit/selection is frozen before the 2026/27 file is
read. The pinned model cannot execute trades, bets, API calls or fund movements.
"""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
from typing import Sequence
import numpy as np

from wolf_lab.cc0_training import SOURCE_REV, CC0,CC0SourceError,load_cc0,featurize,SeasonSource
from wolf_lab.cc0_mlp import Model, fit,proper,validated_comparison, selected_model, SOURCE_MODEL_VERSION

TRAINING_SEASONS = ("2017-18","2018-19","2019-20","2020-21","2021-22","2022-23","2023-24")
VALIDATION_SEASON = "2024-25"
HISTORY_ONLY_SEASON = "2025-26"
FINAL_SEASON = "2026-27"
PINNED_INPUTS = {
"2017-18":"b635f2442a94aa91d85f282fc5e8f7f5dc4f0d04e3e30c4472102f5708d7548c",
"2018-19":"e2224d86f0605a5a1b5b019c845cdecb13aca1d88035686d4159b875250d4730",
"2019-20":"9e1695f85ce5553f762e809dea357ec0a95838939be89569060a83c4e98a302d",
"2020-21":"21ddf26b48469da530c51ccc4857bf1a534bda3aed08766b55185efb142e9a20",
"2021-22":"fbdfd426fa18fa2f8630b77de87c082734da495ac4668d6d72f29f76b73b9564",
"2022-23":"8d09f0f9846981626cdfec48903e1f21e7c79aabe6f92535c9e092e8e79b808b",
"2023-24":"03e13eafbf78dfe00d7e89dd3bf6643986eb6e8fd86c7664aeb8c5bc0bed88d0",
"2024-25":"c3d18f552d83382cd4b6b21127adbbfe38e7f8618ddc979fb5404f2df07d0a75",
"2025-26":"d6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1",
}
SCHEMA="wolf.cc0-frozen-mlp-evidence.v1"
CC0_LICENSE_SHA256="36ffd9dc085d529a7e60e1276d73ae5a030b020313e6c5408593a6ae2af39673"


def _folder_file(folder:Path, season:str,*,expected:str)->SeasonSource:
    return load_cc0(folder/(season+"-en.1.json"),season=season,
                    sha256_expected=expected,allow_missing=(season==HISTORY_ONLY_SEASON or season==FINAL_SEASON))


def _digest(payload)->str:
    return sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def freeze_training(folder:Path,*,source_head:str) ->dict:
    import re
    if not isinstance(source_head,str) or re.fullmatch(r"[0-9a-f]{40}",source_head) is None:
        raise CC0SourceError("frozen Wolf-Coin source HEAD required")
    raw_license=(Path(folder)/"CC0-LICENSE.md").read_bytes()
    if sha256(raw_license).hexdigest()!=CC0_LICENSE_SHA256:
        raise CC0SourceError("CC0 repository license receipt missing or changed")
    source=[_folder_file(folder,season,expected=PINNED_INPUTS[season])
            for season in (*TRAINING_SEASONS,VALIDATION_SEASON)]
    parts=featurize(source)
    train=tuple(r for part in parts[:-1] for r in part)
    validation=parts[-1]
    decision=validated_comparison(train,validation)
    model=selected_model(train,decision)
    result={
        "schema":SCHEMA,"mode":"CC0_OFFLINE_NEURAL_RESEARCH_ONLY",
        "wolf_source_head":source_head,
        "upstream_repo":"https://github.com/openfootball/football.json",
        "upstream_sha":SOURCE_REV,
        "license":"CC0-1.0",
        "license_sha256":CC0_LICENSE_SHA256,
        "dataset_sha256":{s:PINNED_INPUTS[s] for s in (*TRAINING_SEASONS,VALIDATION_SEASON)},
        "coverage":{x.season:{"scored":x.scored,"unscored":x.unscored} for x in source},
        "selection":decision,
        "selected_model":asdict(model) if model else None,
        "model_notes":"Two predeclared methods, linear and 8-unit MLP; selection against training class prior only, not market odds.",
        "future_test_season":FINAL_SEASON,
        "2025_26_history_only":"2025/26 OpenFootball source incomplete (353/380); used for pre-2026/27 feature history if needed, never training in this v1.",
        "future_test_dataset_not_loaded":True,
        "financial_edge_proven":False,"live_enabled":False,
        "sup_training_authorized":False,
    }
    result["frozen_digest"]="sha256:"+_digest(result)
    return result


def evaluate_frozen(folder:Path, record:dict, final_digest:str)->dict:
    if not isinstance(record,dict) or record.get("schema")!=SCHEMA:
        raise CC0SourceError("missing trained model evidence")
    copy=dict(record)
    seal=copy.pop("frozen_digest",None)
    if seal != "sha256:"+_digest(copy):
        raise CC0SourceError("frozen model manifest digest mismatch")
    import re
    if re.fullmatch(r"[0-9a-f]{40}",str(record.get("wolf_source_head",""))) is None:
        raise CC0SourceError("unbound Wolf-Coin model source revision")
    if record.get("upstream_sha")!=SOURCE_REV or record.get("license")!=CC0 or record.get("license_sha256")!=CC0_LICENSE_SHA256:
        raise CC0SourceError("model source/rights binding mismatch")
    if record.get("dataset_sha256")!={s:PINNED_INPUTS[s] for s in (*TRAINING_SEASONS,VALIDATION_SEASON)}:
        raise CC0SourceError("model training input hashes changed")
    if not record.get("future_test_dataset_not_loaded"):
        raise CC0SourceError("test set contaminated prior to freeze")
    if record.get("selected_model") is None:
        return {"status":"ABSTAIN_NO_MODEL","live_admission":False,"financial_edge_proven":False}
    # Loading all history reconstructs the exact prior-date state for the new
    # season; the incomplete 2025/26 results are used solely as earlier form.
    sources=[_folder_file(folder,s,expected=PINNED_INPUTS[s])
             for s in (*TRAINING_SEASONS, VALIDATION_SEASON,HISTORY_ONLY_SEASON)]
    sources.append(_folder_file(folder,FINAL_SEASON,expected=final_digest))
    if sources[-1].scored<30:
        raise CC0SourceError("too few scored fixtures to evaluate this partial season")
    groups=featurize(sources)
    scored=tuple(r for r in groups[-1] if r.label is not None)
    model=Model(**record["selected_model"])
    predictions=model.predict(scored)
    outcomes=np.asarray([r.label for r in scored],dtype=np.int64)
    evaluation=proper(outcomes,predictions)
    # Cross-project bookmaker prices are deliberately not used in this neural
    # training or score-only holdout, so no inference of monetary EV is made.
    output={
       "schema":"wolf.cc0-future-evaluation.v1",
       "model_frozen_digest":seal,
       "source_revision":SOURCE_REV,
       "heldout_season":FINAL_SEASON,
       "heldout_sha256":final_digest,
       "heldout_scored":sources[-1].scored,
       "heldout_unscored":sources[-1].unscored,
       "prior_history_2025_26_scored":sources[-2].scored,
       "prior_history_2025_26_unscored":sources[-2].unscored,
       "selected_model":record["selection"]["selected_kind"],
       "proper_scores":evaluation,
       "pre_declared_baseline":"training outcome-frequency baseline",
       "no_real_or_virtual_bets":True,
       "no_quote_or_provider_timestamp_proof":True,
       "financial_edge_proven":False,
       "live_admission":False,
       "new_unseen_holdout_used_once":True,
       "caveat":"Latest season is incomplete and the result is provisional; not a future profitability claim.",
    }
    return output


def _write(path:Path,payload):
    path=path.resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        json.dump(payload,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n");f.flush();os.fsync(f.fileno())


def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="wolf-cc0")
    sub=p.add_subparsers(dest="operation",required=True)
    for op in ("freeze","evaluate"):
        sp=sub.add_parser(op)
        sp.add_argument("--data-root",type=Path,required=True)
        sp.add_argument("--output",type=Path,required=True)
        if op=="freeze":
            sp.add_argument("--source-head",required=True)
        if op=="evaluate":
            sp.add_argument("--frozen-model",type=Path,required=True)
            sp.add_argument("--final-sha256",required=True)
    args=p.parse_args(argv)
    try:
        if args.operation=="freeze":
            result=freeze_training(args.data_root,source_head=args.source_head)
        else:
            result=evaluate_frozen(args.data_root,
                    json.loads(args.frozen_model.read_text()),args.final_sha256)
        _write(args.output,result)
        print(json.dumps({
            "status":"CC0_RESEARCH_ONLY",
            "operation":args.operation,
            "model_selected":result.get("selection",{}).get("selected_kind") if args.operation=="freeze" else result.get("selected_model"),
            "future_score":result.get("proper_scores"),
            "funding_ready":False,
            "output":str(args.output.resolve())
        },sort_keys=True))
        return 0
    except (CC0SourceError,ValueError,OSError,TypeError,KeyError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc),"funding_ready":False}),file=__import__("sys").stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
