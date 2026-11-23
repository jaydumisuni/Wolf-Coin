from __future__ import annotations

from datetime import date
import hashlib
import json

import pytest

from wolf_lab.backtest import ResearchBlocked, evaluate_heldout, ingest_results


def fixture(tmp_path,name,year,records=24):
    rows=[]
    for i in range(records):
        rows.append({"date":f"{year}-09-{1+i%25:02d}","team1":f"Home {i}",
                     "team2":f"Away {i}",
                     "score":{"ft":[2,0] if i%3==0 else [1,1] if i%3==1 else [0,1]}})
    p=tmp_path/name
    p.write_text(json.dumps({"name":"test","matches":rows})+"\n")
    return ingest_results(p,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def test_fixed_sha_prevents_training_from_wrong_file(tmp_path):
    t=fixture(tmp_path,"train.json",2024)
    with pytest.raises(ResearchBlocked,match="digest mismatch"):
        ingest_results(t.origin,expected_sha256="0"*64)


def test_realistic_older_train_newer_holdout_is_reproducible(tmp_path):
    train=fixture(tmp_path,"train.json",2024)
    hold=fixture(tmp_path,"hold.json",2025)
    a=evaluate_heldout(train,hold)
    b=evaluate_heldout(train,hold)
    assert a==b
    assert a["train_count"]==a["holdout_count"]==24
    assert a["profit_qualified"] is False and a["can_place_bets"] is False
    assert a["no_bookmaker_prices"] is True
    assert a["train_last_day"]<a["holdout_first_day"]
    assert sum(a["heldout_outcomes"].values())==24


def test_future_train_or_leak_is_rejected(tmp_path):
    older=fixture(tmp_path,"old.json",2024)
    newer=fixture(tmp_path,"new.json",2025)
    with pytest.raises(ResearchBlocked,match="training dates overlap"):
        evaluate_heldout(newer,older)
    with pytest.raises(ResearchBlocked,match="identical evidence"):
        evaluate_heldout(older,older)


def test_score_list_and_dict_both_supported(tmp_path):
    rows=[{"date":f"2024-08-{i+1:02d}","team1":f"Home {i}",
           "team2":f"Away {i}","score":[1,0] if i%2 else {"ft":[0,0]}} for i in range(21)]
    p=tmp_path/"score.json";p.write_text(json.dumps({"matches":rows}))
    ds=ingest_results(p)
    assert len(ds.matches)==21
    assert {x.outcome for x in ds.matches}=={"home","draw"}


def test_duplicate_match_prevents_replay(tmp_path):
    p=tmp_path/"duplicate.json"
    one={"date":"2024-08-01","team1":"A","team2":"B","score":[2,1]}
    p.write_text(json.dumps({"matches":[one for _ in range(25)]}))
    with pytest.raises(ResearchBlocked,match="duplicate"):
        ingest_results(p)


@pytest.mark.parametrize("score",[
    None, {}, {"ht":[2,1]}, [1], [1,0.5], [True,0], [-1,0], [0,51], "1-0"])
def test_missing_or_invalid_results_fail_closed(tmp_path,score):
    rows=[{"date":f"2024-08-{i+1:02d}","team1":f"A{i}",
           "team2":f"B{i}","score":score} for i in range(21)]
    p=tmp_path/"wrong.json";p.write_text(json.dumps({"matches":rows}))
    with pytest.raises(ResearchBlocked):
        ingest_results(p)


def test_insufficient_sample_rejected(tmp_path):
    p=tmp_path/"small.json"
    p.write_text(json.dumps({"matches":[{"date":"2024-08-01","team1":"A","team2":"B","score":[2,1]}]}))
    with pytest.raises(ResearchBlocked,match="insufficient"):
        ingest_results(p)


def test_invalid_smoothing_rejected(tmp_path):
    a=fixture(tmp_path,"train.json",2024)
    b=fixture(tmp_path,"hold.json",2025)
    for v in (-1.0,100.0,1):
        with pytest.raises(ResearchBlocked):
            evaluate_heldout(a,b,laplace=v)
