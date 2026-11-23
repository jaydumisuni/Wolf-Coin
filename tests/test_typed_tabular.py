"""Adversarial source-bound tabular model adapter qualification.

Proves a distinct stdlib checker can reproduce the frozen NumPy MLP without
importing the trainer. It does not qualify Formula math certification, SUP's
Soup methods, a financial strategy or a new holdout period.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from wolf_lab.typed_tabular import (
    TypedRouteRefused, build, verify, digest, load_frozen,
    _validated_weights, predict_independently, MODEL_FROZEN_DIGEST,
    MODEL_FROZEN_FILE_SHA256, MODEL_FROZEN_SOURCE,
    EXPECTED_FINAL_SOURCE_SHA256,
    PREDICTION_TOLERANCE,
)


@pytest.fixture(scope="module")
def real_proof():
    root=Path("/home/kratos/projects/Wolf-Coin/.workspace")
    frozen=root/"proof-history/cc0-neural-20261123/frozen-model-170a555.json"
    datasets=root/"research/external/openfootball-cc0-20261123"
    if not (frozen.exists() and datasets.is_dir()):
        pytest.skip("pinned local CC0 proof not available on this test host")
    model=load_frozen(frozen)
    packet=build(frozen,datasets)
    return frozen,datasets,model,packet


def mutate_and_seal(packet:dict, mutate):
    out=deepcopy(packet)
    mutate(out)
    unsigned=dict(out)
    unsigned.pop("candidate_digest",None)
    out["candidate_digest"]="sha256:"+digest(unsigned)
    return out


def test_independent_numerical_verification_matches_frozen_model(real_proof):
    frozen,data,model,packet=real_proof
    result=verify(packet,frozen,data)
    assert result["status"]=="NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY"
    assert result["evaluated_rows"]==45
    assert result["max_abs_probability_error"]<=PREDICTION_TOLERANCE
    assert result["formula_mathematical_authority"] is False
    assert result["sup_method_admitted"] is False
    assert result["neural_training_executed"] is False
    assert result["funding_ready"] is False and result["live_admission"] is False
    assert packet["model_frozen_digest"]==MODEL_FROZEN_DIGEST
    assert packet["model_file_sha256"]==MODEL_FROZEN_FILE_SHA256
    assert packet["model_source_head"]==MODEL_FROZEN_SOURCE
    assert packet["evaluated_sha256"]==EXPECTED_FINAL_SOURCE_SHA256
    assert packet["evaluated_scored_count"]==45
    assert packet["classes"]==["H","D","A"]
    assert packet["candidate_digest"]=="sha256:"+digest({
        key:value for key,value in packet.items() if key!="candidate_digest"
    })


def test_second_build_is_identical(real_proof):
    frozen,data,_,packet=real_proof
    assert build(frozen,data)==packet


@pytest.mark.parametrize("name,modify",[
    ("changed score", lambda p:p["predictions"][0]["class_probabilities"].__setitem__(0,0.95)),
    ("changed feature", lambda p:p["predictions"][0]["prior_day_features"].__setitem__(0,9000.0)),
    ("swapped fixture", lambda p:p["predictions"][0].__setitem__("id","2026-08-01|unknown|unknown")),
    ("false admission", lambda p:p.__setitem__("live_admission",True)),
    ("fake Formula authority", lambda p:p.__setitem__("independent_formula_mathematical_certificate",True)),
    ("SUP method approval", lambda p:p.__setitem__("sup_sim_route_qualified",True)),
    ("external model training", lambda p:p.__setitem__("trained_against_new_2026_27_evidence",True)),
    ("money", lambda p:p.__setitem__("financial_edge_proven",True)),
    ("foreign product", lambda p:p.__setitem__("target_product","Other")),
    ("switch season", lambda p:p.__setitem__("evaluated_season","2025-26")),
    ("wrong output count", lambda p:p.__setitem__("evaluated_scored_count",46)),
    ("extra execution flag", lambda p:p.__setitem__("broker_execute",True)),
])
def test_resigned_attacks_refused_even_when_digest_recomputed(real_proof,name,modify):
    frozen,data,_,packet=real_proof
    forged=mutate_and_seal(packet,modify)
    with pytest.raises(TypedRouteRefused):
        verify(forged,frozen,data)


def test_content_change_without_seal_refused(real_proof):
    frozen,data,_,packet=real_proof
    forged=deepcopy(packet)
    forged["predictions"][0]["class_probabilities"][1]=0.75
    with pytest.raises(TypedRouteRefused,match="digest mismatch"):
        verify(forged,frozen,data)


def test_model_tamper_is_rejected_by_independently_pinned_file_hash(real_proof,tmp_path):
    frozen,data,_,packet=real_proof
    changed=json.loads(frozen.read_text())
    changed["selected_model"]["b"][0] += 0.001
    dst=tmp_path/"tampered-model.json"
    dst.write_text(json.dumps(changed,sort_keys=True))
    with pytest.raises(TypedRouteRefused,match="independently pinned digest"):
        verify(packet,dst,data)


@pytest.mark.parametrize("bad_model",[
    {"kind":"mlp","mean":[],"scale":[],"a":[],"b":[],"c":[],"d":[]},
    {"kind":"llm-70B","mean":[],"scale":[],"a":[],"b":[],"c":[],"d":[]},
    {"kind":"mlp","mean":[float("nan")]*10,"scale":[1]*10,"a":[[1]*8]*10,
     "b":[0]*8,"c":[[1]*3]*8,"d":[0]*3},
    {"kind":"mlp","mean":[0]*10,"scale":[0]*10,"a":[[1]*8]*10,
     "b":[0]*8,"c":[[1]*3]*8,"d":[0]*3},
])
def test_dimensions_and_nonfinite_weights_fail(bad_model):
    with pytest.raises(TypedRouteRefused):
        _validated_weights(bad_model)


def test_probabilities_need_valid_feature_dimension(real_proof):
    _,_,model,_=real_proof
    with pytest.raises(TypedRouteRefused,match="dimension mismatch"):
        predict_independently(model["selected_model"],[0.5])


def test_pure_stdlib_replay_with_all_site_packages_disabled(real_proof,tmp_path):
    frozen,data,_,packet=real_proof
    candidate=tmp_path/"candidate.json"
    candidate.write_text(json.dumps(packet,sort_keys=True))
    result=tmp_path/"verification.json"
    completed=subprocess.run(
        [sys.executable,"-S","-m","wolf_lab.typed_tabular","verify",
         "--frozen",str(frozen),"--data-root",str(data),
         "--candidate",str(candidate),"--output",str(result)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])},
        text=True,capture_output=True,check=False,timeout=20,
    )
    assert completed.returncode==0,completed.stderr
    evidence=json.loads(result.read_text())
    assert evidence["status"]=="NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY"
    assert evidence["evaluated_rows"]==45


def test_replay_training_regenerates_bit_identical_weights_and_selection(real_proof):
    from wolf_lab.typed_tabular import replay_training
    frozen,data,_,_=real_proof
    report=replay_training(frozen,data)
    assert report["status"]=="PRODUCT_OWNED_CPU_TRAINING_REPRODUCED"
    assert report["train_rows"]==2660 and report["validation_rows"]==380
    assert report["replayed_model_sha256"]==report["reference_model_sha256"]
    assert report["replayed_selection_sha256"]==report["reference_selection_sha256"]
    assert report["new_future_data_loaded"] is False
    assert report["no_market_odds_training"] is True
    assert report["independent_training_algorithm"] is False
    assert report["sup_or_soup_method_approved"] is False
    assert report["live_admission"] is False


def test_training_never_loads_history_only_or_examined_2026_27(real_proof,monkeypatch):
    import wolf_lab.typed_tabular as adapter
    frozen,data,_,_=real_proof
    actual=adapter.load_cc0
    observed=[]

    def audited_source(*args,**kwargs):
        observed.append(kwargs["season"])
        if kwargs["season"] in ("2025-26","2026-27"):
            raise AssertionError("post-validation source leakage")
        return actual(*args,**kwargs)

    monkeypatch.setattr(adapter,"load_cc0",audited_source)
    report=adapter.replay_training(frozen,data)
    assert report["train_rows"]==2660
    assert set(observed)==set(adapter.TRAINING_SEASONS)|{adapter.VALIDATION_SEASON}


def test_replay_training_detects_changed_source_material(real_proof,tmp_path):
    from wolf_lab.typed_tabular import replay_training,TRAINING_SEASONS,VALIDATION_SEASON
    frozen,data,_,_=real_proof
    for season in (*TRAINING_SEASONS,VALIDATION_SEASON):
        original=data/(season+"-en.1.json")
        (tmp_path/original.name).write_bytes(original.read_bytes())
    target=tmp_path/"2022-23-en.1.json"
    target.write_bytes(target.read_bytes()+b" ")
    from wolf_lab.cc0_training import CC0SourceError
    with pytest.raises(CC0SourceError,match="hash mismatch"):
        replay_training(frozen,tmp_path)


def test_training_replay_cli_in_research_mode(real_proof,tmp_path):
    frozen,data,_,_=real_proof
    result=tmp_path/"trainer-report.json"
    job=subprocess.run(
        [sys.executable,"-m","wolf_lab.typed_tabular","retrain-proof",
         "--frozen",str(frozen),"--data-root",str(data),
         "--output",str(result)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])},
        text=True,capture_output=True,check=False,timeout=20)
    assert job.returncode==0,job.stderr
    report=json.loads(result.read_text())
    assert report["status"]=="PRODUCT_OWNED_CPU_TRAINING_REPRODUCED"
    assert report["replayed_model_sha256"]==report["reference_model_sha256"]
    assert json.loads(job.stdout)["funding_ready"] is False


def test_guarded_outputs_refuse_overwriting_existing_proof(real_proof,tmp_path):
    frozen,data,_,packet=real_proof
    candidate=tmp_path/"candidate.json"
    candidate.write_text(json.dumps(packet))
    result=tmp_path/"proof.json"
    result.write_text("preexisting")
    completed=subprocess.run(
        [sys.executable,"-S","-m","wolf_lab.typed_tabular","verify",
         "--frozen",str(frozen),"--data-root",str(data),
         "--candidate",str(candidate),"--output",str(result)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])},
        text=True,capture_output=True,check=False,timeout=20,
    )
    assert completed.returncode==2 and result.read_text()=="preexisting"
    assert json.loads(completed.stderr)["status"]=="BLOCKED"
