"""No holdout reuse, proper-score gating and bounded daily stakes."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
import pytest

from wolf_lab.odds_replay import ReplayRefused, ReplayPolicy, load_season
from wolf_lab.walkforward import walk_forward, _validate, BLEND_WEIGHTS

from test_odds_replay import season


def tri(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2022,8,1),n=80)
    b,hb=season(tmp_path,"validation.csv",date(2023,8,1),n=80,quoted=("2.2","3.1","3.2"),outcome="A")
    c,hc=season(tmp_path,"final.csv",date(2024,8,1),n=80,quoted=("1.9","3.4","4.0"),outcome="H")
    return [load_season(p,expected_sha256=h) for p,h in ((a,ha),(b,hb),(c,hc))]


def test_three_windows_one_frozen_selection_and_exposure_bounds(tmp_path):
    t,v,f=tri(tmp_path)
    a=walk_forward(t,v,f)
    b=walk_forward(t,v,f)
    assert a==b
    assert a["train_matches"]==a["validation_matches"]==a["final_matches"]==80
    assert a["selected_blend_weight"] in BLEND_WEIGHTS or a["selected_blend_weight"] is None
    assert not a["future_profit_proven"] and not a["live_admission"]
    assert a["final"]["bets"] <= a["final"]["holdout_days"]
    for item in a["final"]["ledger"]:
        prev=Decimal(item["balance_virtual_ZMW"])-Decimal(item["net_virtual_ZMW"])
        assert Decimal(item["stake_virtual_ZMW"]) <= prev*Decimal("0.005")
        assert Decimal(item["offered_opening_odds"])<=Decimal("5")


def test_reversed_validation_period_denied(tmp_path):
    t,v,f=tri(tmp_path)
    with pytest.raises(ReplayRefused,match="chronological"):
        walk_forward(v,t,f)


def test_final_period_cannot_repeat_validation(tmp_path):
    t,v,f=tri(tmp_path)
    with pytest.raises(ReplayRefused,match="chronological"):
        walk_forward(t,v,v)


def test_selection_uses_only_training_validation(tmp_path):
    t,v,f=tri(tmp_path)
    selected,baseline,scores=_validate(t,v,ReplayPolicy())
    assert selected is None or selected in BLEND_WEIGHTS
    assert isinstance(baseline,float)
    assert len(scores)==len(BLEND_WEIGHTS)


def test_no_calibration_edge_causes_complete_abstention(tmp_path,monkeypatch):
    import wolf_lab.walkforward as wf
    t,v,f=tri(tmp_path)
    monkeypatch.setattr(wf,"MIN_BRIER_IMPROVEMENT",float("inf"))
    x=wf.walk_forward(t,v,f)
    assert x["selected_blend_weight"] is None
    assert x["final"]["bets"]==0
    assert x["final"]["net_virtual_ZMW"]=="0.000000"
    assert x["decision"]=="ABSTAIN_NO_VALIDATED_FORECAST_EDGE"


def test_real_validation_result_cannot_override_release_gate(tmp_path):
    t,v,f=tri(tmp_path)
    x=walk_forward(t,v,f)
    assert x["live_admission"] is False
    assert x["future_profit_proven"] is False

def test_three_window_cli_writes_offline_report_and_has_no_live_effect(tmp_path,capsys):
    import json
    from wolf_lab.walkforward_cli import main
    train,ht=season(tmp_path,"t.csv",date(2022,8,1),n=80)
    valid,hv=season(tmp_path,"v.csv",date(2023,8,1),n=80)
    final,hf=season(tmp_path,"f.csv",date(2024,8,1),n=80)
    # Identical season match bodies are not identical bytes due to different years.
    report=tmp_path/"result.json";html=tmp_path/"result.html"
    args=["--train",str(train),"--train-sha256",ht,
          "--validation",str(valid),"--validation-sha256",hv,
          "--final",str(final),"--final-sha256",hf,
          "--report-json",str(report),"--report-html",str(html)]
    assert main(args)==0
    stdout=json.loads(capsys.readouterr().out)
    assert stdout["status"]=="HISTORICAL_RESEARCH_ONLY"
    assert stdout["live_admission"] is False
    assert report.is_file() and html.is_file()
    assert "<script>" not in html.read_text()
    assert main(args)==2  # fail closed on overwrite
    assert json.loads(capsys.readouterr().err)["status"]=="BLOCKED"
