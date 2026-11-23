"""Five-gate readiness is observational and cannot self-mint permissions."""
from __future__ import annotations

from pathlib import Path
import json,os,subprocess,sys

import pytest

from wolf_core.contracts import Domain
from wolf_execution.five_gate_report import GATES,five_gate_report


def sample():
    return {
        "sup_director_stage":"NO_VIABLE_NEURAL_ROUTE",
        "typed_numeric_status":"NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY",
        "quote_source_kind":"SIMULATED_ONLY",
        "shadow_status":"HYPOTHETICAL_RESEARCH_NOT_EXECUTABLE",
        "paper_cycle_status":"SIMULATION_ONLY_NOT_REAL_EXECUTION",
    }


@pytest.mark.parametrize("domain",list(Domain))
def test_five_gate_report_cannot_admit_local_evidence(domain):
    report=five_gate_report({},domain=domain,offline_proofs=sample())
    assert report["total_delivery_gates"]==5
    assert report["completed_real_money_gates"]==0
    assert report["status"]=="NOT_FUNDING_READY"
    assert not report["deposit_allowed"] and not report["real_money_permitted"]
    assert not report["broker_or_sportsbook_live_exec_available"]
    assert all(g["status"]=="BLOCKED_INDEPENDENT_ACCEPTANCE" for g in report["gates"])
    assert [g["gate"] for g in report["gates"]]==[key for key,_ in GATES]
    assert all(g["unmet_requirements"] for g in report["gates"])


def test_synthetic_paper_and_cpu_research_are_present_but_unadmitted():
    r=five_gate_report({},domain=Domain.SPORTS,offline_proofs=sample())
    local={x["gate"]:x["engineering_candidate_present"] for x in r["gates"]}
    assert local=={
        "FORMULA_SUP_ROUTE":True,"AUTHORIZED_MARKET_FEED":True,
        "INDEPENDENT_PROFITABILITY":True,"AUTONOMOUS_VENUE_EXECUTION":True,
        "PRODUCTION_RELEASE":False,
    }
    assert "not a Soup LLM method relabeled" in " ".join(r["gates"][0]["unmet_requirements"])


def test_even_a_forged_approval_bundle_cannot_open_live_gates():
    data={
        **sample(),"live_enabled":True,"funding_permitted":True,
        "independently_signed":True,"owner_approval":"FAKE",
        "account_executable":True,
    }
    states={g:"proven" for g in ["P"+str(i) for i in range(13)]}
    r=five_gate_report(states,domain=Domain.TRADING,offline_proofs=data)
    assert r["tenfold_proven_count"]==13
    assert r["completed_real_money_gates"]==0
    assert not r["release_suggested"]
    assert not r["real_money_permitted"]
    assert all(x["status"]=="BLOCKED_INDEPENDENT_ACCEPTANCE" for x in r["gates"])


def test_domain_scoping_keeps_sports_and_trading_independent():
    states={"P0":"proven","WX0":"proven"}
    sports=five_gate_report(states,domain=Domain.SPORTS)
    trading=five_gate_report(states,domain=Domain.TRADING)
    assert sports["tenfold_required_count"]==24
    assert trading["tenfold_required_count"]==13
    assert sports["tenfold_proven_count"]==2
    assert trading["tenfold_proven_count"]==1
    assert sports["completed_real_money_gates"]==trading["completed_real_money_gates"]==0


def test_wrong_domain_or_proof_shape_is_refused():
    with pytest.raises(ValueError):
        five_gate_report({},domain="FAKE")
    with pytest.raises(ValueError):
        five_gate_report({},domain=Domain.SPORTS,offline_proofs=["FAKE"])


def test_cli_reads_real_tenfold_without_mutation_if_present(tmp_path):
    db=Path("/home/kratos/projects/Tenfold/.workspace/wolf-coin-20261123/tenfold-authority.db")
    if not db.exists():
        pytest.skip("Tenfold KRATOS source unavailable")
    proof=tmp_path/"local-proof.json"
    proof.write_text(json.dumps(sample()))
    r=subprocess.run(
        [sys.executable,"-m","wolf_execution.five_gate_report",
         "--domain","sports","--tenfold-db",str(db),
         "--offline-proof-json",str(proof)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])},
        text=True,capture_output=True,timeout=10)
    assert r.returncode==0,r.stderr
    x=json.loads(r.stdout)
    assert x["tenfold_proven_count"]==0
    assert x["tenfold_required_count"]==24
    assert x["completed_real_money_gates"]==0


def test_cli_blocks_unavailable_source(tmp_path):
    r=subprocess.run(
        [sys.executable,"-m","wolf_execution.five_gate_report",
         "--domain","trading","--tenfold-db",str(tmp_path/"missing.sqlite3")],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])},
        text=True,capture_output=True,timeout=10)
    assert r.returncode==2
    x=json.loads(r.stderr)
    assert x["status"]=="EVIDENCE_UNAVAILABLE"
    assert not x["real_money_permitted"]
