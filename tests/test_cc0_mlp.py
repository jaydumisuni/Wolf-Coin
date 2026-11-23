"""Source-bound CC0 neural research, no oracle bookmaker training or live funds."""
from __future__ import annotations
from datetime import date,timedelta
from dataclasses import replace
import hashlib,json
from pathlib import Path
import numpy as np
import pytest

from wolf_lab.cc0_training import (
    CC0SourceError,Fixture,SeasonSource,load_cc0,featurize,_team
)
from wolf_lab.cc0_mlp import (
    Model,MLPError,fit,proper,validated_comparison,selected_model
)
from wolf_lab.cc0_pipeline import freeze_training,evaluate_frozen,CC0_LICENSE_SHA256,PINNED_INPUTS,SCHEMA


def season(tmp_path,name,start:date,*,n=100,finished=True):
    p=tmp_path/(name+"-en.1.json")
    rows=[]
    for i in range(n):
        day=start+timedelta(days=i//2)
        gf=(i*7//3)%4
        ga=(i*5//6)%3
        rows.append({
            "date":day.isoformat(),"team1":f"H{i%13} FC","team2":f"A{i%13}",
            "score":{"ft":[gf,ga]} if finished else {}
        })
    p.write_text(json.dumps({"name":name,"matches":rows}))
    return p,hashlib.sha256(p.read_bytes()).hexdigest()


def grouped(tmp_path):
    sources=[]
    for i in range(8):
        name=f"{2017+i}-{str(18+i)}"
        p,d=season(tmp_path,name,date(2017+i,8,1))
        sources.append(load_cc0(p,season=name,sha256_expected=d))
    return featurize(sources)


def test_public_domain_normalization_across_years():
    assert _team("Manchester United FC")==_team("Manchester United")
    assert _team("AFC Bournemouth")==_team("Bournemouth FC")
    assert _team("ARSENAL FC")==_team("Arsenal")


def test_lagged_features_identical_regardless_same_day_outcome():
    first=Fixture(date(2023,8,1),"a","b",2,0,"2023-24")
    alternate=replace(first,home_goals=0,away_goals=4)
    later=Fixture(date(2023,8,2),"a","c",1,2,"2023-24")
    source=SeasonSource("2023-24","x",(first,later),2,0)
    source2=SeasonSource("2023-24","y",(alternate,later),2,0)
    a=featurize((source,))[0]
    b=featurize((source2,))[0]
    assert a[0].features==b[0].features
    assert a[1].features!=b[1].features


def test_leakage_same_day_is_forbidden_even_if_teams_repeat():
    day=date(2022,8,1)
    one=Fixture(day,"a","b",3,1,"2022-23")
    two=Fixture(day,"a","c",0,1,"2022-23")
    a=featurize((SeasonSource("2022-23","x",(one,two),2,0),))[0]
    assert a[0].features==a[1].features
    assert all(np.isfinite(x) for r in a for x in r.features)


def test_hash_validation_and_incomplete_rejection(tmp_path):
    p,d=season(tmp_path,"2023-24",date(2023,8,1),n=90)
    with pytest.raises(CC0SourceError,match="hash mismatch"):
        load_cc0(p,season="2023-24",sha256_expected="0"*64)
    p,d=season(tmp_path,"2025-26",date(2025,8,1),n=90,finished=False)
    with pytest.raises(CC0SourceError,match="incomplete season"):
        load_cc0(p,season="2025-26",sha256_expected=d)
    s=load_cc0(p,season="2025-26",sha256_expected=d,allow_missing=True)
    assert s.unscored==90 and s.scored==0
    assert all(x.label is None for x in featurize((s,))[0])


def test_tampered_schedule_duplicate_refused(tmp_path):
    p,d=season(tmp_path,"2023-24",date(2023,8,1),n=90)
    obj=json.loads(p.read_text())
    obj["matches"][1]=obj["matches"][0]
    p.write_text(json.dumps(obj))
    dig=hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(CC0SourceError,match="duplicate fixture"):
        load_cc0(p,season="2023-24",sha256_expected=dig)


def test_model_only_sees_scored_training_and_valid_sequence(tmp_path):
    parts=grouped(tmp_path)
    train=tuple(r for group in parts[:-1] for r in group)
    validation=parts[-1]
    d=validated_comparison(train,validation)
    assert d["train_rows"]==700 and d["validation_rows"]==100
    assert d["decision"] in ("MODEL_QUALIFIED_FOR_FRESH_SCORE_ONLY",
                              "ABSTAIN_NO_VALIDATED_FORECAST_IMPROVEMENT")
    assert d["live_admission"] is False
    assert d["financial_edge_proven"] is False
    model=fit(train,"mlp")
    p=model.predict(validation)
    assert p.shape==(100,3) and np.allclose(p.sum(axis=1),1)
    assert all(np.isfinite(v) for v in proper(np.asarray([r.label for r in validation]),p).values())


def test_unscored_training_and_untrusted_methods_refused(tmp_path):
    parts=grouped(tmp_path)
    train=list(parts[0]+parts[1]+parts[2]+parts[3]+parts[4])
    with pytest.raises(MLPError,match="non-predeclared"):
        fit(train,"transformer-70B")
    train[0]=replace(train[0],label=None)
    with pytest.raises(MLPError,match="unscored"):
        fit(train,"mlp")


def test_training_is_deterministic_and_serializable(tmp_path):
    parts=grouped(tmp_path)
    train=tuple(r for group in parts[:5] for r in group)
    val=parts[5]
    a=fit(train,"mlp")
    b=fit(train,"mlp")
    assert np.array_equal(a.predict(val),b.predict(val))
    from dataclasses import asdict
    roundtrip=Model(**json.loads(json.dumps(asdict(a))))
    assert np.array_equal(a.predict(val),roundtrip.predict(val))


def test_bad_scores_and_future_labels_refuse_proper_score():
    with pytest.raises(MLPError,match="unplayed"):
        proper(np.asarray([None],dtype=object),np.asarray([[0.4,0.3,0.3]]))
    with pytest.raises(MLPError,match="invalid prediction probabilities"):
        proper(np.asarray([1],dtype=np.int64),np.asarray([[0.4,0.3,0.2]]))


def test_pinned_local_real_coverage_and_manifest_oracle():
    folder=Path('/home/kratos/projects/Wolf-Coin/.workspace/research/external/openfootball-cc0-20261123')
    if not folder.is_dir():
        pytest.skip("real CC0 material only on KRATOS")
    assert hashlib.sha256((folder/"CC0-LICENSE.md").read_bytes()).hexdigest()==CC0_LICENSE_SHA256
    record=freeze_training(folder,source_head="a"*40)
    assert record["selected_model"] is not None
    assert record["selection"]["validation_rows"]==380
    assert record["selection"]["train_rows"]==2660
    assert record["future_test_dataset_not_loaded"]
    assert not record["financial_edge_proven"] and not record["live_enabled"]
    assert len(record["dataset_sha256"])==8
    assert record["selection"]["candidates"]["mlp"]["brier"]==0.623347533
    assert not (folder/"2026-27-en.1.json").exists(), "holdout must not be read before source freeze"


def test_forged_freeze_or_unseen_does_not_create_live_authority():
    fake={"schema":SCHEMA,"license":"CC0-1.0","upstream_sha":"forged",
          "frozen_digest":"sha256:"+"0"*64}
    with pytest.raises(CC0SourceError,match="digest mismatch"):
        evaluate_frozen(Path("/unavailable"),fake,"0"*64)


def test_source_head_required_to_freeze_local_material():
    from wolf_lab.cc0_pipeline import freeze_training
    with pytest.raises(CC0SourceError,match="source HEAD"):
        freeze_training(Path("/unavailable"),source_head="untrusted")
