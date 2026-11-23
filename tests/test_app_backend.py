"""Application backend lifecycle and adversarial finance/session boundary."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from hashlib import sha256
import json,os,sqlite3,subprocess,sys,hmac,hashlib

import pytest

from wolf_app.bridge import process
from wolf_app.contracts import REQUEST_SCHEMA
from wolf_app.store import ApplicationStore,AppConflict


def instant(shift=0):
    return (datetime.now(timezone.utc)+timedelta(seconds=shift)).isoformat()


def message(i,op,data):
    return json.dumps({"schema":REQUEST_SCHEMA,"request_id":i,
                       "operation":op,"payload":data},sort_keys=True)


def send(store,i,op,data):
    return process(store,message(i,op,data))


@pytest.fixture()
def app(tmp_path):
    db=tmp_path/"application.sqlite3"
    store=ApplicationStore(db)
    return store,db


def register(store, *,domain="sports",account="user1",currency="ZMW",
             platform="example",display="Example Account",request="r1"):
    return send(store,request,"account.register",{
        "domain":domain,"account_id":account,"platform_id":platform,
        "currency":currency,"display_name":display})


def activate(store,*,domain="sports",account="user1",
             session="local_tab_a",request="s1",shift=0):
    return send(store,request,"session.record",{
        "domain":domain,"account_id":account,"state":"ACTIVE",
        "session_ref":session,"observed_at":instant(shift)})


def observe(store,*,domain="sports",account="user1",session="local_tab_a",
            observation="obs1",request="o1",shift=0, source="DOM",
            fields=None,transactions=None):
    return send(store,request,"observation.ingest",{
        "domain":domain,"account_id":account,"observation_id":observation,
        "session_ref":session,"observed_at":instant(shift),
        "source":source,"origin":"www.example.invalid",
        "evidence_sha256":sha256((observation+source).encode()).hexdigest(),
        "fields":fields or {
            "cash_balance":"120.50","available_balance":"100.00",
            "pending_bets":"15.00","realized_pnl":"-2.15",
            "unrealized_pnl":"8.75","fees_total":"1.25"},
        "transactions":transactions or []})


def read(store,domain="sports",account="user1"):
    return send(store,"read1","account.read",{"domain":domain,"account_id":account})


def test_account_registration_and_session_recovery_across_restart(app):
    store,db=app
    assert register(store)["status"]=="OK"
    assert read(store)["data"]["session_state"]=="LOGGED_OUT"
    assert activate(store)["data"]["session_state"]=="ACTIVE"
    assert observe(store)["data"]["verification"]=="UNVERIFIED"
    initial=read(store)["data"]
    assert initial["freshness"]=="CURRENT_UNVERIFIED"
    assert initial["latest_financial"]["fields"]["realized_pnl"]=="-2.15"
    assert initial["latest_financial"]["fields"]["unrealized_pnl"]=="8.75"
    assert initial["latest_financial"]["verification"]=="UNVERIFIED"
    assert initial["transactions"]==[]
    after=ApplicationStore(db)
    restored=read(after)["data"]
    assert restored["latest_financial"]==initial["latest_financial"]
    assert restored["session_state"]=="ACTIVE"
    assert restored["observation_count"]==1
    assert after.verify_audit()==3


@pytest.mark.parametrize("state",["LOGGED_OUT","EXPIRED","OFFLINE","PAUSED"])
def test_logged_out_expired_offline_paused_keep_account_but_mark_stale(app,state):
    store,_=app
    register(store)
    activate(store)
    observe(store)
    result=send(store,"s2","session.record",{
        "domain":"sports","account_id":"user1",
        "state":state,"observed_at":instant()})
    assert result["status"]=="OK"
    after=read(store)["data"]
    assert after["session_state"]==state
    assert after["freshness"]=="STALE_LAST_KNOWN"
    assert after["latest_financial"]["fields"]["available_balance"]=="100.00"
    assert after["observation_count"]==1
    assert after["registered_at"]


def test_relogin_uses_new_local_session_and_does_not_trust_old_observation(app):
    store,_=app
    register(store)
    activate(store)
    observe(store)
    send(store,"s2","session.record",{
        "domain":"sports","account_id":"user1",
        "state":"LOGGED_OUT","observed_at":instant()})
    activate(store,session="another_session",request="s3")
    old=read(store)["data"]
    assert old["session_state"]=="ACTIVE"
    assert old["freshness"]=="STALE_LAST_KNOWN"
    blocked=observe(store,request="o2",observation="obs2")
    assert blocked["status"]=="REJECTED"
    assert observe(store,session="another_session",observation="obs2",request="o3")["status"]=="OK"
    assert read(store)["data"]["freshness"]=="CURRENT_UNVERIFIED"


def test_transactions_pending_then_settled_not_double_counted(app):
    store,_=app
    register(store)
    activate(store)
    when=instant(-5)
    transaction={"transaction_id":"tx100","kind":"DEPOSIT","amount":"25.00",
                 "status":"PENDING","occurred_at":when}
    assert observe(store,transactions=[transaction])["status"]=="OK"
    x=read(store)["data"]
    assert x["transactions"][0]["status"]=="PENDING"
    transaction["status"]="SETTLED"
    x=observe(store,observation="obs2",request="o2",transactions=[transaction])
    assert x["status"]=="OK"
    txs=read(store)["data"]["transactions"]
    assert len(txs)==1 and txs[0]["status"]=="SETTLED"
    assert txs[0]["amount"]=="25.00"
    assert store.verify_audit()==4


def test_transaction_conflicting_amount_refused_rollback_all(app):
    store,_=app
    register(store)
    activate(store)
    when=instant(-10)
    transaction={"transaction_id":"tx100","kind":"FEE","amount":"5.00",
                 "status":"SETTLED","occurred_at":when}
    observe(store,transactions=[transaction])
    transaction["amount"]="500.00"
    out=observe(store,request="o2",observation="obs2",transactions=[transaction])
    assert out["status"]=="REJECTED"
    before=read(store)["data"]
    assert before["observation_count"]==1
    assert before["transactions"][0]["amount"]=="5.00"
    assert store.verify_audit()==3


def test_duplicate_request_and_rebound_request_id_fails_closed(app):
    store,_=app
    data={"domain":"sports","account_id":"user1","platform_id":"example",
          "currency":"ZMW","display_name":"Test"}
    a=send(store,"same","account.register",data)
    assert send(store,"same","account.register",data)==a
    data["currency"]="USD"
    assert send(store,"same","account.register",data)["status"]=="REJECTED"
    assert store.verify_audit()==1


def test_foreign_currency_never_combined_into_zmw(app):
    store,_=app
    register(store)
    register(store,domain="trading",account="u2",currency="USD",request="r2")
    activate(store)
    activate(store,domain="trading",account="u2",session="t_session",request="s2")
    observe(store)
    observe(store,domain="trading",account="u2",session="t_session",
            observation="ot2",request="o2",fields={
                "cash_balance":"500.00","available_balance":"400.00",
                "realized_pnl":"12.00"})
    overview=send(store,"all","financial.overview",{})["data"]
    assert overview["currency_totals"]["ZMW"]["available_balance"]=="100.00"
    assert overview["currency_totals"]["USD"]["available_balance"]=="400.00"
    assert overview["cross_currency_conversion"] is False
    assert overview["settled_funds_verified"] is False


def test_removal_cascades_finance_session_decisions_but_preserves_audit(app):
    store,_=app
    register(store)
    activate(store)
    observe(store)
    assert send(store,"del1","account.remove",{"domain":"sports","account_id":"user1"})["status"]=="OK"
    assert send(store,"list","accounts.list",{})["data"]["accounts"]==[]
    assert read(store)["status"]=="REJECTED"
    assert store.verify_audit()==4


def test_observation_does_not_accept_secrets_or_claims_of_verification(app):
    store,_=app
    register(store)
    activate(store)
    suspicious=json.loads(message("x","observation.ingest",{
        "domain":"sports","account_id":"user1","observation_id":"o2",
        "session_ref":"local_tab_a","observed_at":instant(),"source":"DOM",
        "origin":"www.example.invalid","evidence_sha256":"a"*64,
        "fields":{"cash_balance":"10.00"},"cookie":"session=secret"}))
    assert process(store,json.dumps(suspicious))["status"]=="REJECTED"
    assert observe(store,fields={"cash_balance":"10.0","verified":"true"})["status"]=="REJECTED"
    assert store.verify_audit()==2


@pytest.mark.parametrize("value",["NaN","1e6","-1.00","50000000000000000000","10.123456789","12,500.00"])
def test_bad_or_out_of_range_balance_rejected(app,value):
    store,_=app
    register(store)
    activate(store)
    assert observe(store,fields={"available_balance":value})["status"]=="REJECTED"


def test_old_observation_retained_without_overwriting_current(app):
    store,_=app
    register(store)
    activate(store)
    observe(store,shift=-10,observation="old",request="o1",
            fields={"available_balance":"1.00"})
    observe(store,shift=0,observation="new",request="o2",
            fields={"available_balance":"2.00"})
    result=observe(store,shift=-5,observation="middle",request="o3",
                   fields={"available_balance":"100000.00"})
    assert result["data"]["older_than_previous"] is True
    assert read(store)["data"]["latest_financial"]["fields"]["available_balance"]=="2.00"
    assert read(store)["data"]["observation_count"]==3


def test_financial_decision_is_native_workflow_not_forced_analysis_mode(app):
    store,_=app
    register(store)
    activate(store)
    observe(store)
    result=send(store,"d1","decision.propose",{
        "domain":"sports","account_id":"user1","decision_id":"candidate1",
        "observation_id":"obs1","instrument":"fixture_one",
        "action_kind":"PLACE_BET","proposed_amount":"0.50",
        "browser_capabilities":["PLACE_BET"],
        "platform_permissions":["TRANSACT"],"money_budget":"2.00",
        "target_id":"offer_1"})
    assert result["status"]=="OK"
    assert result["data"]["status"]=="BROWSER_HANDOFF_READY"
    assert result["data"]["native_workflow_ready"] is True
    assert result["data"]["context_selection"]["native_browser_handoff"]["kind"]=="PLACE_BET"
    bad=send(store,"d2","decision.receipt",{
        "domain":"sports","account_id":"user1","decision_id":"candidate1",
        "outcome":"SETTLED","result_ref":"unverified_result"})
    assert bad["status"]=="REJECTED"
    accepted=send(store,"d3","decision.receipt",{
        "domain":"sports","account_id":"user1","decision_id":"candidate1",
        "outcome":"UNKNOWN","result_ref":"browser_unknown"})
    assert accepted["data"]["status"]=="UNKNOWN"
    replay=send(store,"d4","decision.receipt",{
        "domain":"sports","account_id":"user1","decision_id":"candidate1",
        "outcome":"NOT_EXECUTED","result_ref":"retry"})
    assert replay["status"]=="REJECTED"
    decisions=send(store,"dl","decisions.list",{"domain":"sports","account_id":"user1"})
    assert decisions["data"]["decisions"][0]["status"]=="UNKNOWN"
    assert decisions["data"]["execution_handoff"]=="NATIVE_BROWSER"


def test_corrupt_audit_chain_is_detected(app):
    store,db=app
    register(store)
    assert store.verify_audit()==1
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE app_audit SET event_json=? WHERE seq=1",('{"forged":true}',))
    with pytest.raises(AppConflict,match="audit"):
        store.verify_audit()


def test_bounded_line_ipc_subprocess_and_no_listener(tmp_path):
    db=tmp_path/"child.sqlite3"
    base={"schema":REQUEST_SCHEMA,"request_id":"one",
          "operation":"bridge.capabilities","payload":{}}
    from wolf_app.bridge import _initialize_native_key
    key=tmp_path/"native.key"
    _initialize_native_key(key)
    p=subprocess.run([sys.executable,"-m","wolf_app.bridge",
                      "--db",str(db),"--key-file",str(key)],
        input=signed_request(base,key.read_bytes())+"\n"+
              signed_request({**base,"request_id":"two","operation":"accounts.list"},
                             key.read_bytes())+"\n",
        capture_output=True,text=True,timeout=10,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])})
    assert p.returncode==0,p.stderr
    lines=[json.loads(x) for x in p.stdout.splitlines()]
    assert len(lines)==2
    assert lines[0]["data"]["browser_adapter_connected"] is False
    assert lines[0]["data"]["network_listener"] is False
    assert lines[0]["data"]["credential_storage"] is False
    assert lines[1]["status"]=="OK"
    if os.name=="posix":
        assert db.stat().st_mode & 0o777 == 0o600


def test_duplicate_json_key_and_oversized_ipc_refused(app):
    store,_=app
    assert process(store,'{"schema":"x","schema":"y"}')["status"]=="REJECTED"
    assert process(store,"z"*70_000)["status"]=="REJECTED"


def test_separate_domain_registration_and_no_fake_live_capabilities(app):
    store,_=app
    register(store)
    register(store,domain="trading",account="user1",request="other")
    caps=send(store,"cap","bridge.capabilities",{})["data"]
    assert caps["financial_workflow"]=="CONTEXTUAL_NATIVE_BROWSER_HANDOFF"
    assert caps["financial_intent_kinds"]==["PLACE_BET","CANCEL_BET","PLACE_TRADE","CLOSE_POSITION"]
    assert "live_order_submission" not in caps
    assert caps["all_observations_external_unverified"] is True
    assert len(send(store,"list","accounts.list",{})["data"]["accounts"])==2


def test_correlated_browser_channels_are_only_corrob_unverified(app):
    store,_=app
    register(store)
    activate(store)
    observe(store,source="DOM",observation="dom1",request="o1",fields={
        "cash_balance":"20.00","available_balance":"17.00"})
    observe(store,source="VISIBLE_NETWORK",observation="net1",request="o2",fields={
        "cash_balance":"20.00","available_balance":"17.00"})
    record=read(store)["data"]
    assert record["reconciliation"]["status"]=="CROSS_CHECKED_UNVERIFIED"
    assert record["reconciliation"]["independently_platform_verified"] is False
    assert record["freshness"]=="CURRENT_UNVERIFIED"


def test_conflicting_financial_sources_block_currency_aggregation(app):
    store,_=app
    register(store)
    activate(store)
    observe(store,source="DOM",observation="dom1",request="o1",fields={
        "cash_balance":"20.00","available_balance":"17.00"})
    observe(store,source="VISIBLE_NETWORK",observation="net1",request="o2",fields={
        "cash_balance":"20.00","available_balance":"1700.00"})
    record=read(store)["data"]
    assert record["freshness"]=="CONFLICTED_UNVERIFIED"
    assert record["reconciliation"]["status"]=="CONFLICT"
    assert record["reconciliation"]["conflicting_fields"]==["available_balance"]
    overview=send(store,"overview","financial.overview",{})["data"]
    assert overview["currency_totals"]=={}
    assert not overview["settled_funds_verified"]


def test_sync_plan_queue_claim_observation_receipt_and_restart(app):
    store,db=app
    register(store)
    plan=send(store,"plan","sync.plan",{})["data"]
    assert plan["accounts"][0]["recommendation"]=="WAITING_FOR_LOGIN"
    queued=send(store,"j1","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"sync1","reason":"STARTUP"})
    assert queued["data"]["status"]=="WAITING_LOGIN"
    activate(store)
    claimed=send(store,"c1","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "session_ref":"local_tab_a"})
    assert claimed["status"]=="OK"
    assert claimed["data"]["browser_command"]["kind"]=="OBSERVE_ACCOUNT"
    assert claimed["data"]["operation_class"]=="OBSERVATION"
    after=ApplicationStore(db)
    cannot_claim_again=send(after,"c2","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "session_ref":"local_tab_a"})
    assert cannot_claim_again["status"]=="REJECTED"
    assert send(after,"pending","sync.plan",{})["data"]["accounts"][0]["recommendation"]=="WAITING_FOR_READBACK"
    assert observe(after)["status"]=="OK"
    done=send(after,"jdone","sync.receipt",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "outcome":"OBSERVED","observation_id":"obs1"})
    assert done["data"]["status"]=="DONE"
    inbox=send(after,"inbox","sync.inbox",{"domain":"sports","account_id":"user1"})
    assert inbox["data"]["jobs"][0]["status"]=="DONE"
    assert send(after,"next","sync.plan",{})["data"]["accounts"][0]["recommendation"]=="UP_TO_DATE_UNVERIFIED"
    assert after.verify_audit()==6


def test_unknown_sync_claim_never_auto_replays_or_duplicates_work(app):
    store,db=app
    register(store)
    activate(store)
    send(store,"j1","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"sync1","reason":"MANUAL"})
    send(store,"c1","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "session_ref":"local_tab_a"})
    second=ApplicationStore(db)
    assert send(second,"j2","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"sync2",
        "reason":"PERIODIC"})["status"]=="REJECTED"
    assert send(second,"c2","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "session_ref":"local_tab_a"})["status"]=="REJECTED"
    outcome=send(second,"receipt","sync.receipt",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "outcome":"UNKNOWN"})
    assert outcome["data"]["status"]=="UNKNOWN"
    assert send(second,"j3","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"sync3",
        "reason":"RECONNECT"})["status"]=="REJECTED"
    assert send(second,"plan","sync.plan",{})["data"]["accounts"][0]["recommendation"]=="WAITING_FOR_READBACK"


def test_failed_sync_does_not_claim_verified_observation(app):
    store,_=app
    register(store)
    activate(store)
    send(store,"j1","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"sync1","reason":"PERIODIC"})
    send(store,"c1","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "session_ref":"local_tab_a"})
    assert send(store,"r1","sync.receipt",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "outcome":"OBSERVED","observation_id":"not_observed"})["status"]=="REJECTED"
    assert send(store,"r2","sync.receipt",{
        "domain":"sports","account_id":"user1","job_id":"sync1",
        "outcome":"FAILED"})["data"]["status"]=="FAILED"
    assert send(store,"r3","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"sync2",
        "reason":"RECONNECT"})["status"]=="OK"


def test_secret_fields_with_alias_names_forbidden(app):
    store,_=app
    for field in ("cookie","access_token","refresh_token","password","private_key"):
        request=json.loads(message("bad_"+field,"account.register",{
            "domain":"sports","account_id":"user1","platform_id":"example",
            "currency":"ZMW","display_name":"Test"}))
        request["payload"][field]="secret-content"
        assert process(store,json.dumps(request))["status"]=="REJECTED"
    assert store.verify_audit()==0


def test_bounded_paged_financial_history_and_device_metadata(app):
    store,_=app
    register(store)
    event=send(store,"dev1","session.record",{
        "domain":"sports","account_id":"user1","state":"ACTIVE",
        "session_ref":"local_tab_a","observed_at":instant(),
        "device_id":"ATHENA"})
    assert event["status"]=="OK"
    observe(store,request="o1",observation="obs1",shift=-2,fields={
        "cash_balance":"90.00","available_balance":"80.00"})
    observe(store,request="o2",observation="obs2",fields={
        "cash_balance":"100.00","available_balance":"95.00"})
    assert read(store)["data"]["device_id"]=="ATHENA"
    one=send(store,"history1","financial.history",{
        "domain":"sports","account_id":"user1","kind":"OBSERVATIONS",
        "limit":1,"offset":0})
    assert one["status"]=="OK"
    assert one["data"]["next_offset"]==1
    assert one["data"]["entries"][0]["fields"]["available_balance"]=="95.00"
    assert "session_tag" not in one["data"]["entries"][0]
    two=send(store,"history2","financial.history",{
        "domain":"sports","account_id":"user1","kind":"OBSERVATIONS",
        "limit":1,"offset":1})
    assert two["data"]["entries"][0]["fields"]["available_balance"]=="80.00"
    assert two["data"]["entries"][0]["verification"]=="UNVERIFIED_PLATFORM_REPORTED"


def test_history_transaction_kind_dates_and_cross_account_isolation(app):
    store,_=app
    register(store)
    register(store,domain="trading",account="trader",currency="USD",request="r2")
    activate(store)
    now=instant(-10)
    observe(store,transactions=[{
        "transaction_id":"tx1","kind":"FEE","amount":"2.00",
        "status":"SETTLED","occurred_at":now}])
    t=send(store,"hist","financial.history",{
        "domain":"sports","account_id":"user1","kind":"TRANSACTIONS"})
    assert t["data"]["entries"][0]["amount"]=="2.00"
    assert t["data"]["entries"][0]["status"]=="SETTLED"
    assert t["data"]["platform_settlement_credibility"]=="NOT_EXTERNALLY_VERIFIED"
    other=send(store,"other","financial.history",{
        "domain":"trading","account_id":"trader","kind":"TRANSACTIONS"})
    assert other["data"]["entries"]==[]
    assert send(store,"fail","financial.history",{
        "domain":"sports","account_id":"user1","kind":"TRANSACTIONS",
        "limit":10000})["status"]=="REJECTED"


def test_claim_cannot_use_observation_created_before_browser_task(app):
    store,_=app
    register(store)
    activate(store)
    observe(store,observation="old",request="o1",shift=-20)
    send(store,"queue","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"job1","reason":"MANUAL"})
    send(store,"claim","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "session_ref":"local_tab_a"})
    before=send(store,"receipt","sync.receipt",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "outcome":"OBSERVED","observation_id":"old"})
    assert before["status"]=="REJECTED"
    assert observe(store,observation="fresh",request="o2")["status"]=="OK"
    after=send(store,"receipt2","sync.receipt",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "outcome":"OBSERVED","observation_id":"fresh"})
    assert after["data"]["status"]=="DONE"


def test_session_reference_is_only_stored_as_hash(app):
    store,db=app
    register(store)
    activate(store,session="tablabel_is_not_a_cookie")
    with sqlite3.connect(db) as conn:
        ref=conn.execute("SELECT session_ref FROM app_sessions").fetchone()[0]
    assert ref!="tablabel_is_not_a_cookie" and len(ref)==64
    state=read(store)["data"]
    assert "local_session_ref" not in state
    assert state["local_session_ref_present"] is True


def signed_request(message_data,key:bytes):
    body=json.dumps(message_data,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    tag=hmac.new(key,body.encode(),hashlib.sha256).hexdigest()
    return json.dumps({**message_data,"auth_tag":tag},sort_keys=True)


def test_native_host_authenticated_ipc_rejects_unsigned_and_tampered(tmp_path):
    from wolf_app.bridge import _initialize_native_key, _read_native_key
    file=tmp_path/"native.key"
    _initialize_native_key(file)
    key=_read_native_key(file)
    assert len(key)==32
    db=tmp_path/"app.sqlite3"
    backend=ApplicationStore(db)
    data={"schema":REQUEST_SCHEMA,"request_id":"r1","operation":"account.register",
          "payload":{"domain":"sports","account_id":"one","platform_id":"example",
                     "currency":"ZMW","display_name":"One"}}
    raw=signed_request(data,key)
    assert process(backend,raw,key=key)["status"]=="OK"
    assert process(backend,json.dumps(data),key=key)["status"]=="REJECTED"
    broken=json.loads(raw)
    broken["payload"]["currency"]="USD"
    assert process(backend,json.dumps(broken),key=key)["status"]=="REJECTED"
    assert backend.verify_audit()==1
    with pytest.raises(FileExistsError):
        _initialize_native_key(file)


def test_host_cli_requires_explicit_authenticated_mode(tmp_path):
    db=tmp_path/"app.sqlite3"
    data={"schema":REQUEST_SCHEMA,"request_id":"r1","operation":"accounts.list","payload":{}}
    command=[sys.executable,"-m","wolf_app.bridge","--db",str(db)]
    env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])}
    p=subprocess.run(command+["--once",json.dumps(data)],
                     capture_output=True,text=True,env=env,timeout=10)
    assert p.returncode==2
    assert "BLOCKED" in p.stderr
    key=tmp_path/"native.key"
    setup=subprocess.run([sys.executable,"-m","wolf_app.bridge","--init-key",str(key)],
                capture_output=True,text=True,env=env,timeout=10)
    assert setup.returncode==0,setup.stderr
    assert "NATIVE_IPC_KEY_CREATED" in setup.stdout
    assert "random" not in setup.stdout
    content=key.read_bytes()
    signed=signed_request(data,content)
    response=subprocess.run(command+["--key-file",str(key),"--once",signed],
                    capture_output=True,text=True,env=env,timeout=10)
    assert response.returncode==0,response.stderr
    assert json.loads(response.stdout)["status"]=="OK"
    unsigned=subprocess.run(command+["--key-file",str(key),"--once",json.dumps(data)],
                    capture_output=True,text=True,env=env,timeout=10)
    assert json.loads(unsigned.stdout)["status"]=="REJECTED"
    if os.name=="posix":
        key.chmod(0o644)
        insecure=subprocess.run(command+["--key-file",str(key),"--once",signed],
                         capture_output=True,text=True,env=env,timeout=10)
        assert insecure.returncode==2
        assert json.loads(insecure.stderr)["status"]=="BLOCKED"


def test_explicit_native_host_restart_invalidates_prior_active_session(app):
    store,db=app
    register(store)
    activate(store)
    observe(store)
    assert read(store)["data"]["freshness"]=="CURRENT_UNVERIFIED"
    restarted=ApplicationStore(db)
    first=send(restarted,"hostboot1","host.startup",{"host_instance_id":"host_run_002"})
    assert first["data"]["sessions_requiring_revalidation"]==1
    assert first["data"]["browser_reauthentication_or_restore_required"] is True
    old=read(restarted)["data"]
    assert old["session_state"]=="PAUSED"
    assert old["freshness"]=="STALE_LAST_KNOWN"
    assert old["latest_financial"]["fields"]["cash_balance"]=="120.50"
    activate(restarted,request="revalidated",session="local_tab_a")
    # Even if the host reports the same session reference, the previous
    # observation must not regain fresh status until reobserved.
    assert read(restarted)["data"]["freshness"]=="STALE_LAST_KNOWN"
    observe(restarted,observation="refresh1",request="refresh_req")
    assert read(restarted)["data"]["freshness"]=="CURRENT_UNVERIFIED"


def test_native_host_restart_marks_inflight_work_unknown_without_retries(app):
    store,db=app
    register(store)
    activate(store)
    send(store,"job","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"capture1","reason":"STARTUP"})
    send(store,"claim","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"capture1",
        "session_ref":"local_tab_a"})
    another=ApplicationStore(db)
    restarted=send(another,"startup","host.startup",{"host_instance_id":"new_run"})
    assert restarted["data"]["inflight_browser_tasks_marked_unknown"]==1
    inbox=send(another,"inbox","sync.inbox",{"domain":"sports","account_id":"user1"})
    assert inbox["data"]["jobs"][0]["status"]=="UNKNOWN"
    activate(another,request="s2")
    assert send(another,"claim2","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"capture1",
        "session_ref":"local_tab_a"})["status"]=="REJECTED"
    assert send(another,"job2","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"capture2",
        "reason":"RECONNECT"})["status"]=="REJECTED"


def test_unknown_browser_observation_reconciles_only_after_fresh_relogin_readback(app):
    store,db=app
    register(store)
    activate(store)
    send(store,"job","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"job1","reason":"MANUAL"})
    send(store,"claim","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "session_ref":"local_tab_a"})
    reboot=ApplicationStore(db)
    assert send(reboot,"startup","host.startup",{"host_instance_id":"new_run"})["status"]=="OK"
    assert send(reboot,"recover1","sync.reconcile",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "observation_id":"old","session_ref":"local_tab_a"})["status"]=="REJECTED"
    activate(reboot,request="relogin")
    assert observe(reboot,request="fresh_req",observation="new_obs")["status"]=="OK"
    out=send(reboot,"recover2","sync.reconcile",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "observation_id":"new_obs","session_ref":"local_tab_a"})
    assert out["status"]=="OK"
    assert out["data"]["recovered_from_unknown"] is True
    assert out["data"]["automatic_replay_performed"] is False
    assert send(reboot,"j2","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"job2","reason":"PERIODIC"})["status"]=="OK"


def test_unknown_sync_job_can_be_explicitly_cancelled_but_not_claimed_again(app):
    store,_=app
    register(store)
    activate(store)
    send(store,"job","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"job1","reason":"ON_LOGIN"})
    send(store,"claim","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "session_ref":"local_tab_a"})
    send(store,"unknown","sync.receipt",{
        "domain":"sports","account_id":"user1","job_id":"job1","outcome":"UNKNOWN"})
    assert send(store,"cancel_bad","sync.cancel",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "reason":"AUTO_RETRY"})["status"]=="REJECTED"
    cancel=send(store,"cancel","sync.cancel",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "reason":"USER_REQUESTED"})
    assert cancel["data"]["status"]=="CANCELLED"
    assert cancel["data"]["last_known_financial_data_may_remain_stale"] is True
    assert send(store,"claim2","sync.claim",{
        "domain":"sports","account_id":"user1","job_id":"job1",
        "session_ref":"local_tab_a"})["status"]=="REJECTED"
    assert send(store,"new","sync.enqueue",{
        "domain":"sports","account_id":"user1","job_id":"job2","reason":"RECONNECT"})["status"]=="OK"


def test_native_refresh_planner_requires_new_observation_after_reauthentication(app):
    store,_=app
    register(store)
    activate(store)
    observe(store)
    send(store,"logoff","session.record",{
        "domain":"sports","account_id":"user1","state":"LOGGED_OUT",
        "observed_at":instant()})
    activate(store,request="relogin",session="local_tab_a")
    assert read(store)["data"]["freshness"]=="STALE_LAST_KNOWN"
    plan=send(store,"plan","sync.plan",{})["data"]
    assert plan["accounts"][0]["recommendation"]=="ENQUEUE_OBSERVE_ACCOUNT"


def test_conflicted_account_cannot_propose_even_research_action(app):
    store,_=app
    register(store)
    activate(store)
    observe(store,source="DOM",request="o1",observation="dom1",
            fields={"available_balance":"15.00"})
    observe(store,source="VISIBLE_NETWORK",request="o2",observation="net1",
            fields={"available_balance":"15000.00"})
    assert read(store)["data"]["freshness"]=="CONFLICTED_UNVERIFIED"
    proposed=send(store,"d1","decision.propose",{
        "domain":"sports","account_id":"user1","decision_id":"bet_proposal",
        "observation_id":"net1","instrument":"game_1",
        "action_kind":"PLACE_BET","proposed_amount":"0.50",
        "browser_capabilities":["PLACE_BET"],"platform_permissions":["TRANSACT"],
        "money_budget":"5.00","target_id":"offer"})
    assert proposed["status"]=="OK"
    assert proposed["data"]["status"]=="CONTEXT_STEP_REQUIRED"
    assert proposed["data"]["selected_next_step"]=="RECONCILE_CONFLICTED_FINANCIAL_STATE"


def test_rejected_untrusted_request_id_is_not_reflected(app):
    store,_=app
    bad=json.dumps({"schema":REQUEST_SCHEMA,"request_id":"<script>alert(1)</script>",
        "operation":"accounts.list","payload":{}})
    reply=process(store,bad)
    assert reply["status"]=="REJECTED"
    assert reply["request_id"]=="invalid"


def test_envelope_schema_operation_set_matches_running_contract():
    from wolf_app.store import ALL_OPERATIONS
    root=Path(__file__).resolve().parents[1]
    document=json.loads((root/"contracts/wolf-app-bridge-v1.schema.json").read_text())
    assert document["properties"]["schema"]["const"]==REQUEST_SCHEMA
    assert set(document["properties"]["operation"]["enum"])==ALL_OPERATIONS
    assert document["additionalProperties"] is False
