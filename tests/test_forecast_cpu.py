"""Historical feature and CPU candidate negative controls; no financial side effects."""
from __future__ import annotations

import csv
from dataclasses import replace
from datetime import date,timedelta
from hashlib import sha256
import json

import numpy as np
import pytest

from wolf_lab.learning_dataset import MatchInput,load_verified,materialize,ReplayRefused
from wolf_lab.forecast_cpu import compare,fit,scores,L2_CANDIDATES


def csv_season(tmp_path, name:str, start:date, *, n=90):
    p=tmp_path/name
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["Date","HomeTeam","AwayTeam","FTHG","FTAG","FTR","B365H","B365D","B365A"])
        w.writeheader()
        for i in range(n):
            # Each team plays no more than one fixture per match date.
            hg=(i*3//7)%4
            ag=(i*2//5)%3
            actual="H" if hg>ag else "D" if hg==ag else "A"
            w.writerow({
                "Date":(start+timedelta(days=i//2)).strftime("%d/%m/%Y"),
                "HomeTeam":f"H{i%11}","AwayTeam":f"A{i%13}",
                "FTHG":hg,"FTAG":ag,"FTR":actual,
                "B365H":"2.25","B365D":"3.10","B365A":"3.75",
            })
    return p,sha256(p.read_bytes()).hexdigest()


def synthetic_partitions(tmp_path):
    seasons=[
        csv_season(tmp_path,"a.csv",date(2022,8,1)),
        csv_season(tmp_path,"b.csv",date(2023,8,1)),
        csv_season(tmp_path,"c.csv",date(2024,8,1)),
        csv_season(tmp_path,"d.csv",date(2025,8,1)),
    ]
    inputs=[load_verified(p,expected_sha256=digest,season=f"test{i}")
            for i,(p,digest) in enumerate(seasons)]
    return seasons,materialize(tuple(inputs))


def test_lagged_features_are_prior_date_only():
    day=date(2023,8,1)
    a=MatchInput(day,"H","A",3,0,"H",(2.2,3.4,3.8),"s1")
    b=MatchInput(day,"C","D",0,1,"A",(2.7,3.1,2.5),"s1")
    c=MatchInput(day+timedelta(days=1),"H","D",1,0,"H",(2.0,3.5,4.1),"s1")
    candidate=materialize(([a,b,c],))[0]
    alternate=materialize(([replace(a,home_goals=0,away_goals=3,outcome="A"),b,c],))[0]
    assert candidate[0].features==alternate[0].features
    assert candidate[1].features==alternate[1].features
    assert candidate[0].home_prior_games==0
    assert candidate[2].features!=alternate[2].features


def test_hash_and_csv_score_consistency(tmp_path):
    f,d=csv_season(tmp_path,"a.csv",date(2022,8,1))
    with pytest.raises(ReplayRefused,match="digest"):
        load_verified(f,expected_sha256="0"*64,season="x")
    text=f.read_text().replace(",0,0,D,",",0,0,H,",1)
    # If synthetic data lacks this exact case, force a controlled tamper.
    if text==f.read_text():
        lines=f.read_text().splitlines()
        data=lines[1].split(",")
        data[6]="A" if data[6]!="A" else "H"
        lines[1]=",".join(data)
        text="\n".join(lines)+"\n"
    f.write_text(text)
    digest=sha256(f.read_bytes()).hexdigest()
    with pytest.raises(ReplayRefused,match="unqualified"):
        load_verified(f,expected_sha256=digest,season="x")


def test_four_periods_materialize_deterministically(tmp_path):
    _,p=synthetic_partitions(tmp_path)
    _,q=synthetic_partitions(tmp_path)
    assert p==q
    assert [len(x) for x in p]==[90]*4
    assert all(abs(sum(r.market)-1)<1e-8 for x in p for r in x)
    assert all(len(r.features)==6 for x in p for r in x)


def test_reversed_dates_refused(tmp_path):
    _,p=synthetic_partitions(tmp_path)
    a=MatchInput(date(2024,8,1),"H","A",1,0,"H",(2.2,3.4,3.2),"late")
    b=MatchInput(date(2023,8,1),"C","D",0,0,"D",(2.2,3.4,3.2),"early")
    with pytest.raises(ReplayRefused,match="overlap or reverse"):
        materialize(([a],[b]))


def test_cpu_fit_and_score_compared_to_market(tmp_path):
    _,p=synthetic_partitions(tmp_path)
    train=p[0]+p[1]
    for lam in L2_CANDIDATES:
        model=fit(train,lam)
        preds=model.predict(p[2])
        assert preds.shape==(90,3)
        assert np.allclose(np.sum(preds,axis=1),1)
        assert all(np.isfinite(v) for v in scores(preds,p[2]).values())
    r=compare(train,p[2],p[3])
    assert r["live_ready"] is False
    assert r["profit_proven"] is False
    assert r["exposed_diagnostic_rows"]==90
    assert r["final_unexamined_period_included"] is False


def test_diagnostic_outcomes_cannot_affect_selection(tmp_path):
    _,p=synthetic_partitions(tmp_path)
    r=compare(p[0]+p[1],p[2],p[3])
    altered=tuple(replace(x,label=(x.label+1)%3) for x in p[3])
    s=compare(p[0]+p[1],p[2],altered)
    assert r["best_candidate_penalty"]==s["best_candidate_penalty"]
    assert r["selected"]==s["selected"]
    assert r["market_validation_scores"]==s["market_validation_scores"]


def test_cpu_model_only_admits_frozen_penalties(tmp_path):
    _,p=synthetic_partitions(tmp_path)
    with pytest.raises(ValueError,match="predeclared"):
        fit(p[0],999.0)


def test_source_bound_sup_intake_fails_closed(tmp_path):
    from wolf_lab.forecast_cli import evaluate_four
    seasons,_=synthetic_partitions(tmp_path)
    paths=[x[0] for x in seasons]
    digests=[x[1] for x in seasons]
    result,features,package,request=evaluate_four(
        paths,digests,source_head="a"*40,sup_generation="sha256:"+"b"*64)
    assert len(features)==4 and all(len(x)==90 for x in features)
    assert result["source_truth_qualified"] is False
    assert not package["neural_realization_allowed"]
    assert request["learning_package"]["source_truth_qualified"] is False
    assert request["autonomous_deploy"] is False
    assert result["live_ready"] is False


def test_invalid_source_digest_does_not_materialize_candidate(tmp_path):
    from wolf_lab.forecast_cli import evaluate_four
    seasons,_=synthetic_partitions(tmp_path)
    with pytest.raises(ReplayRefused,match="digest"):
        evaluate_four([p for p,_ in seasons],["0"*64]*4,
            source_head="a"*40,sup_generation="sha256:"+"b"*64)
