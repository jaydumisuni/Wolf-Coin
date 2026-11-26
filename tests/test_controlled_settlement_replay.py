from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import sqlite3

import pytest

from wolf_app.bridge import process
from wolf_app.contracts import REQUEST_SCHEMA
from wolf_app.store import ApplicationStore, AppConflict
from wolf_lab.loss_feedback import Forecast, LossLearner, FeedbackError, write_immutable
from wolf_lab.controlled_settlement_replay import SCHEMA, replay

def now():
    return datetime.now(timezone.utc).isoformat()

def call(store, rid, op, payload):
    reply=process(store,json.dumps(dict(schema=REQUEST_SCHEMA,request_id=rid,
                                       operation=op,payload=payload)))
    assert reply["status"]=="OK",reply
    return reply["data"]

@pytest.fixture
def fixture(tmp_path):
    db=tmp_path/"controlled.sqlite3"
    store=ApplicationStore(db)
    scope={"domain":"sports","account_id":"fixture-account"}
    call(store,"r1","account.register",dict(scope,platform_id="controlled",currency="USD",
                                           display_name="Synthetic fixture"))
    call(store,"r2","session.record",dict(scope,state="ACTIVE",session_ref="fixture-session",
                                        observed_at=now()))
    def observe(oid,proof,transactions):
        return call(store,oid,"observation.ingest",dict(scope,observation_id=oid,
            session_ref="fixture-session",observed_at=now(),source="DOM",
            origin="fixture.example.invalid",evidence_sha256=proof,
            fields={"available_balance":"20.00"},transactions=transactions))
    observe("obs1",sha256(b"controlled initial").hexdigest(),[])
    learner=LossLearner()
    learner.register(Forecast("decision1","fixture1",
        (datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat().replace("+00:00","Z"),
        (0.6,0.2,0.2),0,sha256(b"frozen fixture model").hexdigest()))
    result=call(store,"r3","decision.propose",dict(scope,decision_id="decision1",
        observation_id="obs1",instrument="fixture1",action_kind="PLACE_BET",
        proposed_amount="1.00",browser_capabilities=["PLACE_BET"],
        platform_permissions=["TRANSACT"],money_budget="2.00",target_id="fixture-offer"))
    assert result["status"]=="BROWSER_HANDOFF_READY"
    result=call(store,"r4","decision.receipt",dict(scope,decision_id="decision1",
        outcome="NATIVE_REPORTED_SUBMITTED",result_ref="transaction1",
        receipt_evidence_sha256=sha256(b"controlled submission").hexdigest()))
    assert result["status"]=="AWAITING_PLATFORM_RECONCILIATION"
    transaction=dict(transaction_id="transaction1",kind="BET",amount="1.00",
                     status="PENDING",occurred_at=now())
    observe("obs2",sha256(b"controlled pending").hexdigest(),[transaction])
    evidence=dict(schema=SCHEMA,controlled_fixture=True,account_id="fixture-account",
        decision_id="decision1",transaction_id="transaction1",observation_id="obs3",
        match_id="fixture1",outcome_label=2,settled_utc=now().replace("+00:00","Z"),
        stake=1.0,decimal_odds=2.0)
    raw=json.dumps(evidence,sort_keys=True).encode()
    return db,learner,raw,observe,transaction

def settle(fixture):
    db,learner,raw,observe,transaction=fixture
    observe("obs3",sha256(raw).hexdigest(),[dict(transaction,status="SETTLED")])
    return db,learner,raw

def test_pending_never_trains(fixture):
    db,learner,raw,_,_=fixture
    with pytest.raises(FeedbackError,match="settled transaction"):
        replay(db,learner,raw)
    assert learner.version==0

def test_controlled_loss_receipt_restart_and_idempotence(fixture,tmp_path):
    db,learner,raw=settle(fixture)
    before=learner.predict((.6,.2,.2))
    updated,report=replay(db,learner,raw)
    after=updated.predict((.6,.2,.2))
    assert learner.version==0 and updated.version==1
    assert after[2]>before[2] and after[0]<before[0]
    assert report["learning_receipt"]["virtual_pnl"]==-1
    assert not report["provider_authentication_proven"]
    assert not report["real_money_profit_proven"]
    journal=tmp_path/"learner.json"
    write_immutable(journal,updated.snapshot())
    restored=LossLearner.from_snapshot(json.loads(journal.read_text()))
    again,replayed=replay(db,restored,raw)
    assert again.snapshot()==restored.snapshot()==updated.snapshot()
    assert replayed==report
    assert ApplicationStore(db).verify_audit()==report["application_audit_count"]

def test_modified_evidence_cannot_update(fixture):
    db,learner,raw=settle(fixture)
    evidence=json.loads(raw)
    evidence["outcome_label"]=0
    with pytest.raises(FeedbackError,match="bytes do not match"):
        replay(db,learner,json.dumps(evidence).encode())
    assert learner.version==0

def test_foreign_account_cannot_update(fixture):
    db,learner,raw=settle(fixture)
    evidence=json.loads(raw)
    evidence["account_id"]="foreign-account"
    with pytest.raises(FeedbackError,match="native submission"):
        replay(db,learner,json.dumps(evidence).encode())

def test_corrupt_application_audit_refused(fixture):
    db,learner,raw=settle(fixture)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE app_audit SET event_json='{}' WHERE seq=1")
    with pytest.raises(AppConflict,match="audit"):
        replay(db,learner,raw)
