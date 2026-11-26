from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json, hmac, hashlib
import pytest
from wolf_app.bridge import process
from wolf_app.store import ApplicationStore
from wolf_app.contracts import REQUEST_SCHEMA

KEY=b"test-only-key-material-32-bytes!"
def stamp(offset=0):
    return (datetime.now(timezone.utc)+timedelta(seconds=offset)).isoformat()

def call(store,rid,op,payload):
    body=dict(schema=REQUEST_SCHEMA,request_id=rid,operation=op,payload=payload)
    raw=json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    body["auth_tag"]=hmac.new(KEY,raw.encode(),hashlib.sha256).hexdigest()
    return process(store,json.dumps(body),key=KEY)

@pytest.fixture
def fixture(tmp_path):
    db=tmp_path/"app.sqlite3"
    store=ApplicationStore(db)
    scope=dict(domain="sports",account_id="fixture_user")
    def request(rid,op,**data):
        return call(store,rid,op,dict(scope,**data))
    assert request("reg","account.register",platform_id="fixture",currency="ZMW",display_name="Synthetic fixture")["status"]=="OK"
    assert request("active","session.record",state="ACTIVE",session_ref="fixture_session",observed_at=stamp(1))["status"]=="OK"
    def capture(rid,obs,offset,transactions=(),origin="fixture.invalid"):
        return request(rid,"observation.ingest",observation_id=obs,session_ref="fixture_session",
            observed_at=stamp(offset),source="DOM",origin=origin,
            evidence_sha256=sha256(obs.encode()).hexdigest(),fields={"available_balance":"100"},
            transactions=list(transactions))
    assert capture("o1","obs1",2)["status"]=="OK"
    assert request("d1","decision.propose",decision_id="decision1",observation_id="obs1",
        instrument="fixture1",action_kind="PLACE_BET",proposed_amount="0.50",
        browser_capabilities=["PLACE_BET"],platform_permissions=["TRANSACT"],
        money_budget="2.00",target_id="offer1")["data"]["status"]=="BROWSER_HANDOFF_READY"
    assert request("d2","decision.receipt",decision_id="decision1",outcome="NATIVE_REPORTED_SUBMITTED",
        result_ref="synthetic_tx",receipt_evidence_sha256="a"*64)["data"]["status"]=="AWAITING_PLATFORM_RECONCILIATION"
    tx=dict(transaction_id="synthetic_tx",kind="BET",amount="0.50",status="PENDING",occurred_at=stamp(3))
    return store,db,scope,request,capture,tx

def readback(store,scope,rid,obs,**override):
    payload=dict(scope,decision_id="decision1",transaction_id="synthetic_tx",
                 observation_id=obs,evidence_sha256=sha256(obs.encode()).hexdigest())
    payload.update(override)
    return call(store,rid,"decision.reconcile",payload)

def test_signed_pending_then_settled_and_restart(fixture):
    store,db,scope,request,capture,tx=fixture
    assert capture("o2","obs2",4,[tx])["status"]=="OK"
    pending=readback(store,scope,"p1","obs2")
    assert pending["data"]["status"]=="PLATFORM_REPORTED_PENDING_UNVERIFIED"
    assert readback(store,scope,"p1","obs2")==pending
    tx["status"]="SETTLED"
    assert capture("o3","obs3",5,[tx])["status"]=="OK"
    restored=ApplicationStore(db)
    final=readback(restored,scope,"p2","obs3")
    assert final["data"]["status"]=="PLATFORM_REPORTED_SETTLED_UNVERIFIED"
    assert final["data"]["learning_label_established"] is False
    assert final["data"]["payout_or_realized_pnl_established"] is False
    assert final["data"]["independently_platform_verified"] is False
    again=ApplicationStore(db)
    assert readback(again,scope,"p2","obs3")==final
    assert readback(again,scope,"p3","obs3")["status"]=="REJECTED"
    assert call(again,"list","decisions.list",scope)["data"]["decisions"][0]["status"]==final["data"]["status"]
    assert again.verify_audit()==9

@pytest.mark.parametrize("bad",["wrong_amount","wrong_origin","wrong_hash","wrong_reference","missing_transaction"])
def test_false_readback_rejected_without_mutation(fixture,bad):
    store,db,scope,request,capture,tx=fixture
    if bad=="wrong_amount":
        tx["amount"]="50"
    if bad!="missing_transaction":
        assert capture("o2","obs2",4,[tx],origin="other.invalid" if bad=="wrong_origin" else "fixture.invalid")["status"]=="OK"
    kwargs={}
    if bad=="wrong_hash":kwargs["evidence_sha256"]="0"*64
    if bad=="wrong_reference":kwargs["transaction_id"]="foreign_tx"
    before=store.verify_audit()
    assert readback(store,scope,"bad","obs2",**kwargs)["status"]=="REJECTED"
    assert store.verify_audit()==before
    assert call(store,"list","decisions.list",scope)["data"]["decisions"][0]["status"]=="AWAITING_PLATFORM_RECONCILIATION"
