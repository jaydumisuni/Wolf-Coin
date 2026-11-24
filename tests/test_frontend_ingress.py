"""A single frontend protocol translator for websites with unseen layouts."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json
import subprocess
import sys

import pytest

from wolf_app.frontend_ingress import normalize_browser_snapshot
from wolf_app.evidence_reasoner import interpret
from wolf_app.store import ApplicationStore
from wolf_app.contracts import REQUEST_SCHEMA
from wolf_app.bridge import process


def source(*,domain="test-site.invalid",auth="probable_authenticated",
           visible="Account Balance\nK750.00\nPending Bets\nK100.00\nNet Profit/Loss\nK60.00",
           opportunities=None,candidates=None):
    return {
        "contract":"wolf.browser.v1",
        "accountId":"local_account_a",
        "url":"https://"+domain+"/wallet",
        "auth":auth,
        "observedAt":datetime.now(timezone.utc).isoformat(),
        "visibleText":visible,
        "candidates":candidates if candidates is not None else {
            "balance":{"source":"Balance","value":750,"currency":"ZMW",
                       "verification":"candidate_only"},
            "pending":{"source":"Pending Bets","value":100,"currency":"ZMW",
                       "verification":"candidate_only"},
            "pnl":{"source":"Net Profit/Loss","value":60,"currency":"ZMW",
                   "verification":"candidate_only"},
        },
        "opportunities":opportunities if opportunities is not None else [],
    }


def test_frontend_browser_snapshot_maps_to_evidence_without_site_adapter():
    snapshot=source(domain="brand-new-bookmaker.invalid")
    dom={"accountId":"local_account_a","nodes":[
        {"tag":"button","text":"Place Bet","role":"button"},
        {"tag":"a","text":"Account Transactions"},
    ]}
    data=normalize_browser_snapshot(snapshot,dom)
    assert data["schema"]=="wolf.browser.evidence.v1"
    assert data["origin"]=="brand-new-bookmaker.invalid"
    assert "auth" not in data
    assert data["browser_auth_state"]=="probable_authenticated"
    report=interpret(data)
    facts={f["semantic_type"] for f in report["facts"]}
    assert "cash_balance" in facts or "available_balance" in facts
    assert "pending_bets" in facts
    assert "realized_pnl" in facts
    assert any(c["semantic_action"]=="PLACE_BET" for c in report["controls"])
    assert report["next_task"]=="SYNC_FINANCES"
    assert not report["site_specific_adapter_used"]


def test_unrecognized_site_fields_remain_interpretable_without_finance():
    snapshot=source(
        domain="totally-unknown-company.invalid",
        visible="Mystery Statistic\n17.5\nOther Value: 45.0",
        candidates={})
    report=interpret(normalize_browser_snapshot(snapshot))
    assert report["next_task"]=="ORGANIZE_NEW_SITE_EVIDENCE"
    assert len(report["facts"])>=2
    assert report["unclassified_count"]>=2
    assert report["site_specific_adapter_used"] is False


def test_frontend_opportunity_goes_to_model_evaluation_not_unjustified_bet():
    opportunity={"market":"Some Match","selection":"Away","kind":"bet",
                 "side":"back","quote":2.15,"currency":"ZMW",
                 "verification":"candidate_only"}
    report=interpret(normalize_browser_snapshot(source(
        domain="new-sports-site.invalid",opportunities=[opportunity])))
    assert report["next_task"]=="EVALUATE_MARKET_WITH_MODELS"
    assert report["markets"][0]["quote"]=="2.15"
    assert report["markets"][0]["market_implied_probability"]=="0.465116"
    assert report["markets"][0]["edge_verified"] is False
    assert report["money_action_executed"] is False


def test_credential_bearing_lines_do_not_leave_native_host_transformer():
    incoming=source(
        visible="Password: opaque_secret\nBalance\nK10.00\nAccess Token: opaque_token",
        candidates={})
    document=normalize_browser_snapshot(incoming)
    serialized=json.dumps(document).lower()
    assert "opaque_secret" not in serialized
    assert "opaque_token" not in serialized
    assert all("password" not in x["label"].lower() for x in document["elements"])


def test_redacted_page_sections_are_not_rejoined_to_fake_numeric_facts():
    s=source(visible="Available Balance\nPassword: opaque_secret\n123456",
             candidates={})
    doc=normalize_browser_snapshot(s)
    assert not doc["elements"]
    assert "opaque_secret" not in json.dumps(doc)


def test_unfamiliar_site_text_values_are_preserved_for_later_learning():
    src=source(domain="entirely-new-site.invalid",
               visible="Named Attribute\nBlue Example\nProduct Series\nSeries Alpha",
               candidates={})
    report=interpret(normalize_browser_snapshot(src))
    unknown=[v for v in report["facts"] if v["semantic_type"]=="UNCLASSIFIED"]
    assert any(v["label"]=="Named Attribute" and
               v["text_value"]=="Blue Example" for v in unknown)
    assert report["site_specific_adapter_used"] is False
    assert report["next_task"]=="ORGANIZE_NEW_SITE_EVIDENCE"


def test_dom_account_is_not_allowed_to_mix_other_browser_profile():
    with pytest.raises(Exception):
        normalize_browser_snapshot(source(),{
            "accountId":"other_account","nodes":[]})


def test_browser_auth_state_changes_task_without_site_specific_switch():
    snapshot=source(auth="login_required")
    report=interpret(normalize_browser_snapshot(snapshot))
    assert report["next_task"]=="RESTORE_AUTHENTICATED_SESSION"


def test_signed_bridge_accepts_generic_frontend_observation_without_goal(tmp_path):
    app=ApplicationStore(tmp_path/"app.sqlite3")
    normalized=normalize_browser_snapshot(source())
    packet={"schema":REQUEST_SCHEMA,"request_id":"reason_from_site","operation":"observation.discover",
            "payload":{"document":normalized}}
    result=process(app,json.dumps(packet))
    assert result["status"]=="OK",result
    assert result["data"]["goal_discovered_without_user_provided_goal"] is True
    assert result["data"]["next_task"]=="SYNC_FINANCES"
    assert result["data"]["facts"]
    assert not result["data"]["money_action_executed"]


def test_normalizer_cli_returns_payload_not_untrusted_browser_auth(tmp_path):
    incoming={"snapshot":source()}
    cmd=subprocess.run(
        [sys.executable,"-m","wolf_app.frontend_ingress"],
        input=json.dumps(incoming),
        capture_output=True,text=True,timeout=10,
        cwd=Path(__file__).resolve().parents[1])
    assert cmd.returncode==0,cmd.stderr
    produced=json.loads(cmd.stdout)
    assert produced["operation"]=="observation.discover"
    assert "auth" not in produced["payload"]["document"]
    assert produced["payload"]["document"]["evidence_sha256"]
    result=interpret(produced["payload"]["document"])
    assert result["next_task"]=="SYNC_FINANCES"


def test_unsafe_raw_browser_url_never_transmitted():
    bad=source()
    bad["url"]="https://user:pass@site.example/account"
    with pytest.raises(Exception):
        normalize_browser_snapshot(bad)
    bad["url"]="http://new-site.invalid/dashboard"
    with pytest.raises(Exception):
        normalize_browser_snapshot(bad)

def test_dom_stale_page_controls_are_not_mixed_with_current_account():
    snap=source()
    dom={"accountId":"local_account_a",
         "url":"https://test-site.invalid/login",
         "observedAt":snap["observedAt"],
         "nodes":[{"tag":"button","text":"Log in"}]}
    evidence=normalize_browser_snapshot(snap,dom)
    assert evidence["dom_controls_match_current_page"] is False
    assert evidence["controls"]==[]
    report=interpret(evidence)
    assert report["dom_controls_match_current_page"] is False
    assert not report["controls"]


def test_current_dom_can_support_general_browser_actions_without_site_adapter():
    snap=source()
    dom={"accountId":"local_account_a","url":snap["url"],
         "observedAt":snap["observedAt"],
         "nodes":[{"tag":"button","text":"Place Bet"}]}
    report=interpret(normalize_browser_snapshot(snap,dom))
    assert report["dom_controls_match_current_page"] is True
    assert report["controls"][0]["semantic_action"]=="PLACE_BET"


def test_explicit_currency_candidate_is_not_doubled_on_ingress():
    s=source(visible="",candidates={
       "balance":{"source":"Available Funds","value":"ZMW 100.00",
                  "currency":"ZMW","verification":"candidate_only"}})
    d=normalize_browser_snapshot(s)
    assert d["elements"]==[{"label":"Available Funds","value":"ZMW 100.00"}]
    report=interpret(d)
    assert report["facts"][0]["decimal"]=="100.00"
    assert report["facts"][0]["currency"]=="ZMW"
