"""Independent data-quality audit and frozen holdout scoring tests."""
from __future__ import annotations
from datetime import date,timedelta
from hashlib import sha256
from pathlib import Path
import csv,json
import pytest

from wolf_lab.cc0_audit import crosscheck_scores,diagnostic_holdout_audit,normalize_for_comparison
from wolf_lab.cc0_training import CC0SourceError


def _fixture_sources(tmp_path,*,count=80,corrupt=False):
    path=tmp_path/"2023-24-en.1.json"
    result=tmp_path/"E0-2324.csv"
    fixtures=[];rows=[]
    for i in range(count):
        day=date(2023,8,1)+timedelta(days=i//2)
        h=f"Home{i%10} FC";a=f"Away{i%10}"
        hg=i%5;ag=i%3
        fixtures.append({"date":day.isoformat(),"team1":h,"team2":a,"score":{"ft":[hg,ag]}})
        rows.append({"Date":day.strftime("%d/%m/%Y"),"HomeTeam":h,"AwayTeam":a,
                     "FTHG":str(hg),"FTAG":str(ag+(i==0 and corrupt))})
    path.write_text(json.dumps({"name":"research fixture","matches":fixtures}))
    with result.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["Date","HomeTeam","AwayTeam","FTHG","FTAG"])
        w.writeheader();w.writerows(rows)
    return (path,sha256(path.read_bytes()).hexdigest(),
            result,sha256(result.read_bytes()).hexdigest())


def test_comparison_aliases_do_not_change_cc0_train_features():
    assert normalize_for_comparison("Tottenham")=="tottenham hotspur"
    assert normalize_for_comparison("Man United")=="manchester united"
    assert normalize_for_comparison("Brighton")=="brighton & hove albion"


def test_source_crosscheck_detects_any_score_mismatch(tmp_path):
    a,ah,b,bh=_fixture_sources(tmp_path,corrupt=True)
    result=crosscheck_scores(a,b,season="2023-24",cc0_hash=ah,csv_hash=bh)
    assert result["matched_fixtures"]==80
    assert result["score_conflicts"]==1
    assert not result["perfectly_reconciled"]


def test_clean_independent_scores_join_by_date_and_teams(tmp_path):
    a,ah,b,bh=_fixture_sources(tmp_path)
    result=crosscheck_scores(a,b,season="2023-24",cc0_hash=ah,csv_hash=bh)
    assert result["matched_fixtures"]==80
    assert result["perfectly_reconciled"]


def test_untrusted_secondary_file_is_refused(tmp_path):
    a,ah,b,bh=_fixture_sources(tmp_path)
    with pytest.raises(ValueError,match="digest mismatch"):
        crosscheck_scores(a,b,season="2023-24",cc0_hash=ah,csv_hash="0"*64)


def test_frozen_audit_rejects_unfrozen_model_source():
    with pytest.raises(ValueError,match="frozen bootstrap"):
        diagnostic_holdout_audit(Path("/missing"),{},final_sha256="0"*64,
                                  bootstrap_iterations=1)


def test_kratos_real_scores_are_reconciled_and_bootstrap_crosses_zero():
    root=Path("/home/kratos/projects/Wolf-Coin/.workspace")
    cc0=root/"research/external/openfootball-cc0-20261123"
    private=root/"research/external/historical-odds-20261123"
    model=root/"proof-history/cc0-neural-20261123/frozen-model-170a555.json"
    if not (cc0.is_dir() and private.is_dir() and model.is_file()):
        pytest.skip("KRATOS independent source evidence unavailable elsewhere")
    for season,name in (("2022-23","2223"),("2024-25","2425")):
        a=cc0/(season+"-en.1.json")
        b=private/("E0-"+name+".csv")
        check=crosscheck_scores(a,b,season=season,
            cc0_hash=sha256(a.read_bytes()).hexdigest(),
            csv_hash=sha256(b.read_bytes()).hexdigest())
        assert check["matched_fixtures"]==380 and check["perfectly_reconciled"]
    record=json.loads(model.read_text())
    r=diagnostic_holdout_audit(cc0,record,final_sha256=
      "bb91f0ab3e8359df163bb9ec98549bfed85e200dd4c32f3bd606b5890d932dd2")
    assert r["count"]==45 and r["distinct_match_days"]==17
    assert r["prior_minus_model_brier_95_percentile_interval"][0]<0
    assert r["prior_minus_model_brier_95_percentile_interval"][1]>0
    assert not r["interval_excludes_zero"] and not r["live_admission"]
    assert r["model_brier"]==0.611911853
