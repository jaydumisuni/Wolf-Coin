"""SUP capability-snapshot reproducibility and fail-closed adversarial tests."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import pytest


FILE = Path(__file__).resolve().parents[1] / "scripts/sup_capability_snapshot.py"
spec=importlib.util.spec_from_file_location("wolf_snapshot",str(FILE))
assert spec is not None and spec.loader is not None
snapshot=importlib.util.module_from_spec(spec)
sys.modules["wolf_snapshot"]=snapshot
spec.loader.exec_module(snapshot)


def _git(*args):
    return subprocess.run(("git",*map(str,args)),capture_output=True,text=True,check=True).stdout.strip()


def test_git_generation_binding_requires_real_commit_object(tmp_path):
    repo=tmp_path/"repo"
    repo.mkdir()
    _git("-C",repo,"init","-q")
    _git("-C",repo,"config","user.name","Wolf test")
    _git("-C",repo,"config","user.email","wolf@example.invalid")
    (repo/"memo.txt").write_text("binding-proof\n")
    _git("-C",repo,"add","memo.txt")
    _git("-C",repo,"commit","-q","-m","revision one")
    old=_git("-C",repo,"rev-parse","HEAD")
    result=snapshot._commit(repo,old,"cookpit")
    assert result["frozen_commit_object_present"] and result["active_head_equals_frozen_pin"]
    (repo/"memo.txt").write_text("later\n")
    _git("-C",repo,"commit","-q","-am","revision two")
    recheck=snapshot._commit(repo,old,"cookpit")
    assert recheck["observed_pinned_generation"]==old
    assert recheck["active_head_equals_frozen_pin"] is False
    with pytest.raises(snapshot.SnapshotRefused,match="unqualified frozen"):
        snapshot._commit(repo,"not-a-real-generation","cookpit")
    with pytest.raises(snapshot.SnapshotRefused,match="evidence command failed"):
        snapshot._commit(repo,"0"*40,"cookpit")


def _kratos_paths():
    top=Path("/home/kratos/projects")
    sup=top/"SUP"
    intake=top/"Wolf-Coin/.workspace/research/sup-sup-bit-forecast-20261123/cc0-mlp-170a555/sup-director-request.json"
    resource=top/"Wolf-Coin/.workspace/research/sup-sup-bit-forecast-20261123/sup-bit-readonly-resource.json"
    if not all(x.exists() for x in (sup/"src/sup_control/director.py",intake,resource)):
        pytest.skip("Connected source projects are not materialized on this test host")
    return top,sup,intake,resource


def test_native_sup_processes_verified_snapshot_without_training(monkeypatch):
    top,sup,intake,resource=_kratos_paths()
    monkeypatch.syspath_prepend(str(sup/"src"))
    from sup_control.bindings import SOUP_REF
    original=snapshot._run

    def faithful_stub(*args,**kwargs):
        if args[:2]==("gh","api"):
            assert f"/{SOUP_REF}" in args[2]
            return SOUP_REF  # the remote hash is checked by real CLI in saved evidence
        return original(*args,**kwargs)

    monkeypatch.setattr(snapshot,"_run",faithful_stub)
    request=json.loads(intake.read_text())
    snap,packet=snapshot.build(
        request,sup_root=sup,cookpit=top/"cookpit",formula=top/"formula",
        srg=top/"SRG/Sergeant",simulation=top/"TTG-Simulation",
        resource_report=resource)
    from sup_control.director import build_director_plan
    from sup_control.common import SUPContractError
    result=build_director_plan(packet)
    assert result["stage"]=="NO_VIABLE_NEURAL_ROUTE"
    assert result["artifacts"]["sup_sim"]["reduction"]["survivors"]==[]
    assert len(result["artifacts"]["sup_sim"]["reduction"]["rejected"])==10
    assert result["authority_granted"] is False
    assert result["training_executed"] is False
    assert snap["frozen_pin_currentness_only"] is True
    assert snap["latest_repository_heads_not_claimed_current"] is True
    assert all(value is None for value in packet["sim_request"]["resources"]["method_fit"].values())
    assert snap["soup_donor"]["tabular_1x2_training_adapter_proven"] is False

    adversarial=deepcopy(packet)
    adversarial["sim_request"]["srg_binding"]["observed_generation"]="not-srg"
    with pytest.raises(SUPContractError,match="current SRG"):
        build_director_plan(adversarial)

    adversarial=deepcopy(packet)
    adversarial["sim_request"]["donor_binding"]["authority_transfer"]=True
    with pytest.raises(SUPContractError,match="donor authority transfer"):
        build_director_plan(adversarial)

    adversarial=deepcopy(packet)
    adversarial["sim_request"]["learning_package"]["source_product"]="Other product"
    with pytest.raises(SUPContractError,match="exactly equal"):
        build_director_plan(adversarial)


def test_generated_snapshot_remains_research_only():
    p=Path("/home/kratos/projects/Wolf-Coin/.workspace/research/sup-sup-bit-forecast-20261123/cc0-mlp-170a555/verified-capability-snapshot-20261123/capability-gate-receipt.json")
    if not p.is_file():
        pytest.skip("source-bound candidate evidence not materialized")
    evidence=json.loads(p.read_text())
    assert evidence["capability_snapshot_inputs_complete"] is True
    assert evidence["sup_director_stage"]=="NO_VIABLE_NEURAL_ROUTE"
    assert evidence["sim_candidates_surviving"]==0
    assert evidence["sim_candidates_rejected"]==10
    assert evidence["snapshot_is_signed_owner_acceptance"] is False
    assert evidence["execution_and_deployment_authority"] is False
    assert evidence["financial_edge_proven"] is False
    assert all(x["refused"] for x in evidence["negative_controls"].values())
