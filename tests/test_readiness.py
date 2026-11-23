from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from wolf_core.contracts import Domain
from wolf_execution.readiness import BASE, SPORTS, CAMPAIGN, observed_tenfold_states, report, main


def test_readiness_has_independent_domain_gate_sets_and_no_live_exceptions():
    sports=report(Domain.SPORTS)
    trading=report(Domain.TRADING)
    assert sports["required_gate_count"]==24 and trading["required_gate_count"]==13
    assert "WX10" in sports["unproven_gates"] and "WX10" not in trading["unproven_gates"]
    assert sports["real_money_permitted"] is False
    assert trading["real_money_permitted"] is False
    assert sports["execution_adapters"] == 0


def test_forged_all_proven_local_snapshot_cannot_confer_money_authority():
    user_claim={name:"proven" for name in SPORTS}
    r=report(Domain.SPORTS,user_claim)
    assert r["proven_gate_count"] == len(SPORTS)
    assert not r["unproven_gates"]
    assert r["real_money_permitted"] is False
    assert r["live_executor_installed"] is False
    assert "signature" in r["note"]


def test_invalid_fake_source_identity_rejected(tmp_path):
    db=tmp_path/"state.sqlite3"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE campaigns(campaign_id TEXT,revision INTEGER,snapshot_json TEXT)")
        c.execute("INSERT INTO campaigns VALUES (?, ?, ?)",(
            CAMPAIGN,2,json.dumps({"campaign_id":CAMPAIGN,"revision":1,"node_states":[]}),))
    with pytest.raises(ValueError,match="revision mismatch"):
        observed_tenfold_states(db)


def test_wrong_campaign_rejected(tmp_path):
    db=tmp_path/"state.sqlite3"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE campaigns(campaign_id TEXT,revision INTEGER,snapshot_json TEXT)")
    with pytest.raises(ValueError,match="identity unavailable"):
        observed_tenfold_states(db)


def test_readiness_cli_missing_database_fails_closed(tmp_path,capsys):
    assert main(["--domain","sports","--tenfold-db",str(tmp_path/"missing")])==2
    d=json.loads(capsys.readouterr().err)
    assert d["real_money_permitted"] is False


def test_readiness_cli_no_evidence_is_safe(capsys):
    assert main(["--domain","trading"])==0
    d=json.loads(capsys.readouterr().out)
    assert d["required_gate_count"]==13
    assert d["real_money_permitted"] is False


def test_local_tenfold_readonly_real_snapshot_matches_current_engineering_state():
    p=Path("/home/kratos/projects/Tenfold/.workspace/wolf-coin-20261123/tenfold-authority.db")
    if not p.is_file():
        pytest.skip("KRATOS Tenfold fixture not available outside workstation")
    states=observed_tenfold_states(p)
    assert states["P0"]=="ready"
    assert all(v!="proven" for v in states.values())
    r=report(Domain.SPORTS,states)
    assert r["proven_gate_count"] == 0
    assert not r["real_money_permitted"]
