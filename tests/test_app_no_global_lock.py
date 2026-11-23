"""Application v2 eliminates global research/paper gating while retaining history."""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import json
import sqlite3

import pytest

from wolf_app.backup import backup, restore
from wolf_app.bridge import process
from wolf_app.contracts import REQUEST_SCHEMA, digest
from wolf_app.store import ApplicationStore, AppConflict


def _req(ident,operation,payload):
    return {"schema":REQUEST_SCHEMA,"request_id":ident,
            "operation":operation,"payload":payload}


def test_product_envelope_has_no_global_financial_disable(tmp_path):
    store=ApplicationStore(tmp_path/"application.sqlite3")
    all_operations=store.handle(_req("cap","bridge.capabilities",{}))
    assert all_operations["schema"]=="wolf.app.bridge.v2"
    assert all_operations["status"]=="OK"
    assert "live_enabled" not in all_operations
    assert "financial_execution_authorized" not in all_operations
    available=all_operations["data"]["financial_intent_kinds"]
    assert available==["PLACE_BET","CANCEL_BET","PLACE_TRADE","CLOSE_POSITION"]
    assert all_operations["data"]["financial_workflow"]=="CONTEXTUAL_NATIVE_BROWSER_HANDOFF"
    assert all_operations["data"]["native_host_adapter"]=="REQUIRES_APPLICATION_BINDING"
    assert "live_order_submission" not in all_operations["data"]


def test_financial_context_ready_but_not_a_permanent_research_mode(tmp_path):
    app=ApplicationStore(tmp_path/"application.sqlite3")
    app.handle(_req("account","account.register",{
        "domain":"trading","account_id":"example","platform_id":"broker",
        "currency":"USD","display_name":"Example"}))
    from datetime import timedelta
    at=lambda offset:(datetime.now(timezone.utc)+timedelta(seconds=offset)).isoformat()
    app.handle(_req("login","session.record",{
        "domain":"trading","account_id":"example","state":"ACTIVE",
        "session_ref":"local_tab","observed_at":at(2)}))
    app.handle(_req("observe","observation.ingest",{
        "domain":"trading","account_id":"example","observation_id":"captured",
        "session_ref":"local_tab","observed_at":at(3),"source":"VISIBLE_NETWORK",
        "origin":"broker.invalid","evidence_sha256":"a"*64,
        "fields":{"available_balance":"40.00"}}))
    body={"domain":"trading","account_id":"example","decision_id":"position1",
          "observation_id":"captured","instrument":"symbol1",
          "action_kind":"PLACE_TRADE","proposed_amount":"5.00",
          "browser_capabilities":["PLACE_TRADE"],
          "platform_permissions":["TRANSACT"],
          "target_id":"order_form","money_budget":"8.00"}
    created=app.handle(_req("propose","decision.propose",body))["data"]
    assert created["status"]=="BROWSER_HANDOFF_READY"
    assert created["context_selection"]["next_step"]=="HANDOFF_TO_NATIVE_FINANCIAL_WORKFLOW"
    assert created["native_workflow_ready"] is True
    assert created["browser_action_executed"] is False
    assert "live_enabled" not in created
    assert "RESEARCH_ONLY" not in json.dumps(created)
    assert app.verify_audit()==4


def test_learn_and_research_are_intelligence_goals_not_account_lock(tmp_path):
    app=ApplicationStore(tmp_path/"application.sqlite3")
    for i,goal in enumerate(("LEARN","RESEARCH","ANALYZE","COMPARE_STRATEGIES")):
        output=app.handle(_req("r"+str(i),"context.route",{
             "goal":goal,"capabilities":[],"permissions":[]}))["data"]
        assert output["state"]=="READY"
        assert output["family"]=="INTELLIGENCE"
        assert "global_feature_lock" not in output
        assert "RESEARCH_ONLY" not in json.dumps(output)
    assert app.verify_audit()==0


def test_v1_research_only_record_migrates_and_preserves_audit(tmp_path):
    db=tmp_path/"application.sqlite3"
    original=ApplicationStore(db)
    original.handle(_req("account","account.register",{
        "domain":"sports","account_id":"one","platform_id":"sports",
        "currency":"ZMW","display_name":"Stored"}))
    original.handle(_req("login","session.record",{
        "domain":"sports","account_id":"one","state":"ACTIVE",
        "session_ref":"tab1","observed_at":datetime.now(timezone.utc).isoformat()}))
    cached_command=_req("legacy_cached","decision.propose",{
        "domain":"sports","account_id":"one","decision_id":"old_decision",
        "observation_id":"observation","instrument":"fixture",
        "action_kind":"RESEARCH_BET","proposed_amount":"1.00"})
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE app_meta SET value='1' WHERE key='schema'")
        connection.execute("""INSERT INTO app_decisions VALUES (?,?,?,?,?,?,?,?,?,?)""",(
            "sports","one","old_decision","observation","fixture","RESEARCH_BET",
            "1.00","RESEARCH_ONLY",None,datetime.now(timezone.utc).isoformat()))
        connection.execute("INSERT INTO app_requests VALUES (?,?,?)",(
            "legacy_cached",digest(cached_command),
            json.dumps({"status":"RESEARCH_ONLY","decision_id":"old_decision",
                        "live_execution_authorized":False,
                        "may_submit_order":False},sort_keys=True)))
    archived=tmp_path/"old-source-backup.sqlite3"
    old_receipt=backup(db,archived)
    assert old_receipt["records_checked"]==2
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT value FROM app_meta WHERE key='schema'").fetchone()[0]=="1"
    migrated=ApplicationStore(db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT value FROM app_meta WHERE key='schema'").fetchone()[0]=="2"
    decisions=migrated.handle(_req("list","decisions.list",{
        "domain":"sports","account_id":"one"}))["data"]["decisions"]
    assert len(decisions)==1
    assert decisions[0]["status"]=="ANALYSIS_ARCHIVED"
    cached=migrated.handle(cached_command)
    assert cached["data"]["status"]=="ANALYSIS_ARCHIVED"
    assert cached["data"]["historical_analysis_record"] is True
    assert "live_execution_authorized" not in cached["data"]
    assert "may_submit_order" not in cached["data"]
    assert migrated.verify_audit()==3
    # Old behavior cannot be invoked as a new application operation.
    bad=process(migrated,json.dumps(_req("old_proposal","decision.propose",{
        "domain":"sports","account_id":"one","decision_id":"legacy2",
        "observation_id":"old","instrument":"fixture",
        "action_kind":"RESEARCH_BET","proposed_amount":"1.00"})))
    assert bad["status"]=="REJECTED"
    assert migrated.verify_audit()==3
    twice=ApplicationStore(db)
    assert twice.verify_audit()==3
    result=tmp_path/"recovered.sqlite3"
    restore(old_archival:=archived,new_db:=result)
    with sqlite3.connect(result) as connection:
        assert connection.execute("SELECT value FROM app_meta WHERE key='schema'").fetchone()[0]=="2"
    restored=ApplicationStore(result)
    assert restored.verify_audit()==4
    assert restored.handle(_req("accounts","accounts.list",{}))["data"]["accounts"][0]["display_name"]=="Stored"


def test_native_cli_has_no_research_unkeyed_product_mode(tmp_path):
    import subprocess,sys,os
    project=Path(__file__).resolve().parents[1]
    env={**os.environ,"PYTHONPATH":str(project)}
    p=subprocess.run([sys.executable,"-m","wolf_app.bridge",
       "--db",str(tmp_path/"db"),"--research-unkeyed"],
       capture_output=True,text=True,timeout=10,env=env)
    assert p.returncode!=0
    assert "unrecognized arguments" in p.stderr
