"""Deterministic loss feedback without account connection or financial actions."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import pytest

from wolf_lab.loss_feedback import (
    Forecast, Settlement, FeedbackError, LossLearner, write_immutable
)
from wolf_lab.prelive_qualification import _bootstrap_by_day, _market_eval_only

MODEL_SHA=sha256(b"frozen-prelive-test-model").hexdigest()


def forecast(pid="pred:test-1",probs=(0.60,0.20,0.20),ver=0,when="2026-01-01T08:00:00Z",selected=0):
    return Forecast(pid,"match:"+pid,when,probs,selected,MODEL_SHA,ver)


def receipt(pid="pred:test-1",label=2,when="2026-01-01T23:59:59Z",sid="settle:test-1"):
    return Settlement(sid,pid,when,label,MODEL_SHA,1.0,2.0)


def test_loss_changes_subsequent_predictions_and_versions():
    x=LossLearner()
    first=forecast()
    x.register(first)
    predicted=x.predict((0.6,0.2,0.2))
    assert predicted==first.probabilities
    result=x.settle(receipt())
    assert result["virtual_pnl"]==-1.0 and not result["won"]
    assert result["learning_version"]==1
    assert result["bias_after"]!=result["bias_before"]
    after=x.predict((0.6,0.2,0.2))
    assert after[2]>predicted[2]
    assert after[0]<predicted[0]
    assert x.settle(receipt())==result
    assert len(x.events)==2 and x.version==1
    assert all(v["kind"] in ("FORECAST","SETTLEMENT") for v in x.events)
    assert x.snapshot()["no_live_execution"] is True


def test_wins_and_losses_both_update_learning_but_not_authority():
    x=LossLearner()
    x.register(forecast())
    x.settle(receipt())
    next_day="2026-01-02T08:00:00Z"
    p=x.predict((0.6,0.2,0.2))
    x.register(forecast("pred:test-2",p,1,next_day,selected=0))
    won=x.settle(receipt("pred:test-2",label=0,
                         when="2026-01-02T23:59:59Z",sid="settle:test-2"))
    assert won["won"] and won["virtual_pnl"]==1.0
    assert x.version==2
    assert all(e["kind"] not in ("ORDER","TRADE") for e in x.events)


def test_reject_outcome_without_precommitted_forecast():
    x=LossLearner()
    with pytest.raises(FeedbackError,match="no precommitted"):
        x.settle(receipt())


def test_reject_conflicts_source_and_duplicate_fixture():
    x=LossLearner()
    x.register(forecast())
    x.register(forecast())  # exact replay of a forecast is idempotent before settlement
    with pytest.raises(FeedbackError,match="conflicting duplicate"):
        x.register(forecast(probs=(.50,.30,.20)))
    with pytest.raises(FeedbackError,match="duplicate fixture"):
        x.register(Forecast("pred:test-2","match:pred:test-1",
                            "2026-01-01T08:00:00Z",(.40,.30,.30),0,MODEL_SHA))
    with pytest.raises(FeedbackError,match="source does not match"):
        x.settle(Settlement("settle:test-1","pred:test-1","2026-01-01T23:59:59Z",1,
                            "0"*64,1.0,2.0))
    with pytest.raises(FeedbackError,match="before forecast"):
        x.settle(receipt(when="2026-01-01T07:59:59Z"))
    x.settle(receipt())
    with pytest.raises(FeedbackError,match="conflicting or repeated"):
        x.settle(receipt(label=1))


def test_no_time_travel_or_same_day_result_leakage():
    x=LossLearner()
    same_day_a=forecast("pred:test-a")
    same_day_b=forecast("pred:test-b")
    x.register(same_day_a)
    x.register(same_day_b)
    assert x.version==0
    x.settle(receipt("pred:test-a",sid="settle:test-a"))
    with pytest.raises(FeedbackError,match="later settled event"):
        x.register(forecast("pred:test-c",ver=1))
    with pytest.raises(FeedbackError,match="predates last journal"):
        x.settle(receipt("pred:test-b",when="2026-01-01T22:59:59Z",sid="settle:test-b"))
    x.settle(receipt("pred:test-b",sid="settle:test-b"))
    assert x.version==2


def test_restart_exact_replay_and_tampering_detected(tmp_path):
    x=LossLearner()
    x.register(forecast())
    x.settle(receipt())
    state=x.snapshot()
    first=write_immutable(tmp_path/"sealed.json",state)
    assert first==sha256((tmp_path/"sealed.json").read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        write_immutable(tmp_path/"sealed.json",state)
    replay=LossLearner.from_snapshot(json.loads((tmp_path/"sealed.json").read_text()))
    assert replay.snapshot()==state
    altered=deepcopy(state)
    altered["events"][1]["data"]["receipt"]["virtual_pnl"]=100
    with pytest.raises(FeedbackError,match="sealed journal"):
        LossLearner.from_snapshot(altered)
    state2=deepcopy(state)
    state2["bias"][0]=0.62
    # Even a forged recomputed outer digest is detected by replayed weights.
    from wolf_lab.loss_feedback import _digest
    state2.pop("seal_sha256")
    state2["seal_sha256"]=_digest(state2)
    with pytest.raises(FeedbackError,match="replayed learning state"):
        LossLearner.from_snapshot(state2)


def test_reject_invalid_inputs_and_nonfinite_probabilities():
    with pytest.raises(FeedbackError,match="probabilities"):
        forecast(probs=(.2,.2,.2))
    with pytest.raises(FeedbackError,match="probabilities"):
        forecast(probs=(float("nan"),.5,.5))
    with pytest.raises(FeedbackError,match="learning version"):
        forecast(ver=-1)
    with pytest.raises(FeedbackError,match="invalid settlement outcome"):
        receipt(label=3)
    with pytest.raises(FeedbackError,match="bounded synthetic odds"):
        Settlement("settle:test-1","pred:test-1","2026-01-01T23:59:59Z",1,
                   MODEL_SHA,1.0,float("inf"))


def test_cluster_bootstrap_requires_many_days():
    with pytest.raises(FeedbackError,match="too few"):
        _bootstrap_by_day(["2026-01-01"]*5,[0.1]*5)


def test_market_evaluation_only_rejects_modified_digest(tmp_path):
    f=tmp_path/"fake.csv"
    f.write_text("Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n01/01/2025,A,B,H,2.0,3.2,4.0\n")
    with pytest.raises(FeedbackError,match="digest mismatch"):
        _market_eval_only(f,"0"*64,[])
