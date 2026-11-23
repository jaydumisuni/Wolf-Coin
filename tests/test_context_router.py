"""Context-aware capability selection: no global lock, no imaginary browser effects."""
from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from wolf_app.context_router import GOALS, route_context
from wolf_app.store import ApplicationStore
from wolf_app.contracts import REQUEST_SCHEMA
from wolf_core.contracts import ContractError


def account(*,domain="sports",session="ACTIVE",freshness="CURRENT_UNVERIFIED"):
    return {
        "domain":domain,
        "account_id":"scoped_account",
        "currency":"ZMW" if domain=="sports" else "USD",
        "session_state":session,
        "freshness":freshness,
    }


def call(store,ident,op,payload):
    return store.handle({
        "schema":REQUEST_SCHEMA,
        "request_id":ident,
        "operation":op,
        "payload":payload,
    })["data"]


def test_intelligence_research_works_without_browser_login_or_financial_gate():
    for goal in ("LEARN","RESEARCH","ANALYZE","COMPARE_STRATEGIES"):
        result=route_context(goal=goal,account=None,capabilities=[],permissions=[])
        assert result["family"]=="INTELLIGENCE"
        assert result["state"]=="READY"
        assert result["next_step"]=="INTELLIGENCE_EVALUATE"
        assert result["native_browser_handoff"]["kind"]=="INTELLIGENCE_EVALUATE"
        assert result["global_feature_lock"] is False


@pytest.mark.parametrize("goal,tool",[
    ("OPEN_PLATFORM","NAVIGATE"),("READ_PAGE","INSPECT"),
    ("CLICK_ELEMENT","CLICK"),("TYPE_TEXT","TYPE"),("SCROLL_PAGE","SCROLL"),
    ("SWITCH_TAB","SWITCH_TAB"),("DOWNLOAD_FILE","DOWNLOAD"),("UPLOAD_FILE","UPLOAD"),
])
def test_normal_browser_capabilities_are_ready_without_financial_gates(goal,tool):
    result=route_context(goal=goal,account=None,
        capabilities=[tool],permissions=["OBSERVE","INTERACT"],target="target_01")
    assert result["state"]=="READY"
    assert result["next_step"]=="HANDOFF_TO_WOLF_BROWSER"
    assert result["native_browser_handoff"]["kind"]==tool
    assert result["financial_action"] is False
    assert result["browser_action_executed"] is False


def test_navigation_can_begin_without_financial_or_site_transaction_permission():
    route=route_context(
        goal="OPEN_PLATFORM",account=None,
        capabilities=["NAVIGATE"],permissions=[])
    assert route["state"]=="READY"
    assert route["native_browser_handoff"]["kind"]=="NAVIGATE"
    assert route["financial_action"] is False
    assert route["global_feature_lock"] is False


def test_missing_browser_affordance_is_discovery_not_permanent_disabling():
    result=route_context(goal="CLICK_ELEMENT",account=None,
        capabilities=["INSPECT"],permissions=["OBSERVE","INTERACT"],target="button_1")
    assert result["state"]=="DISCOVER"
    assert result["next_step"]=="INSPECT_BROWSER_CAPABILITIES"
    assert not result["global_feature_lock"]


def test_account_login_recovery_and_sync_observe_are_contextual():
    for state in ("LOGGED_OUT","EXPIRED","OFFLINE","PAUSED"):
        r=route_context(goal="SYNC_FINANCES",account=account(session=state),
            capabilities=["OBSERVE_ACCOUNT"],permissions=["OBSERVE"])
        assert r["next_step"]=="RESTORE_AUTHENTICATED_SESSION"
        assert r["state"]=="RECOVER"
    r=route_context(goal="SYNC_FINANCES",account=account(freshness="STALE_LAST_KNOWN"),
        capabilities=["OBSERVE_ACCOUNT"],permissions=["OBSERVE"])
    assert r["state"]=="READY"
    assert r["native_browser_handoff"]["kind"]=="OBSERVE_ACCOUNT"
    r=route_context(goal="SYNC_FINANCES",account=account(),
        capabilities=["OBSERVE_ACCOUNT"],permissions=["OBSERVE"])
    assert r["next_step"]=="RECONCILE_CURRENT_OBSERVATIONS"


@pytest.mark.parametrize("goal,domain",[
    ("PLACE_BET","sports"),("CANCEL_BET","sports"),
    ("PLACE_TRADE","trading"),("CLOSE_POSITION","trading"),
])
def test_financial_capabilities_can_be_routed_when_context_supports_them(goal,domain):
    result=route_context(goal=goal,account=account(domain=domain),
        capabilities=[goal],permissions=["TRANSACT"],
        requested_amount="1.25",money_budget="2.00",target="offer_one")
    assert result["state"]=="READY"
    assert result["next_step"]=="HANDOFF_TO_NATIVE_FINANCIAL_WORKFLOW"
    assert result["native_browser_handoff"]["kind"]==goal
    if goal in ("PLACE_BET","PLACE_TRADE"):
        assert result["native_browser_handoff"]["requested_amount"]=="1.25"
    else:
        assert "requested_amount" not in result["native_browser_handoff"]
    assert result["financial_action"] is True
    assert result["global_feature_lock"] is False
    assert result["order_or_bet_submitted"] is False
    assert result["requires_native_host_result"] is True


def test_financial_context_correctly_selects_cause_and_recovery():
    inputs={"goal":"PLACE_BET","account":account(),
            "capabilities":["PLACE_BET"],"permissions":["TRANSACT"],
            "requested_amount":"1.00","money_budget":"2.00"}
    def choose(**updates):
        return route_context(**{**inputs,**updates})
    assert choose(capabilities=[])["next_step"]=="INSPECT_PLATFORM_TRANSACTION_CAPABILITY"
    assert choose(permissions=[])["next_step"]=="CONFIRM_SITE_TRANSACTION_PERMISSION"
    assert choose(account=account(freshness="STALE_LAST_KNOWN"))["next_step"]=="OBSERVE_CURRENT_FINANCIAL_STATE"
    assert choose(account=account(freshness="CONFLICTED_UNVERIFIED"))["next_step"]=="RECONCILE_CONFLICTED_FINANCIAL_STATE"
    assert choose(money_budget=None)["next_step"]=="DETERMINE_ACTION_SIZE_AND_SCOPED_BUDGET"
    assert choose(requested_amount="4.00")["next_step"]=="RESIZE_ACTION_WITHIN_ACCOUNT_BUDGET"
    with pytest.raises(ContractError,match="incompatible"):
        choose(account=account(domain="trading"))


def test_cross_domain_financial_actions_not_mislabeled_as_browser_browsing():
    for goal in ("PLACE_BET","PLACE_TRADE"):
        r=route_context(goal=goal,account=None,capabilities=[goal],
                        permissions=["TRANSACT"],requested_amount="2",money_budget="10")
        assert r["state"]=="RECOVER"
        assert r["next_step"]=="REGISTER_OR_SELECT_ACCOUNT"


def test_database_backed_context_uses_registered_session_and_financial_state(tmp_path):
    store=ApplicationStore(tmp_path/"wolf.sqlite3")
    call(store,"reg","account.register",{
        "domain":"sports","account_id":"one","platform_id":"site",
        "currency":"ZMW","display_name":"Test"})
    payload={"goal":"PLACE_BET","domain":"sports","account_id":"one",
        "capabilities":["PLACE_BET"],"permissions":["TRANSACT"],
        "target_id":"offer_one","requested_amount":"1.00","money_budget":"3.00"}
    logged=call(store,"route_1","context.route",payload)
    assert logged["next_step"]=="RESTORE_AUTHENTICATED_SESSION"
    now=datetime.now(timezone.utc).isoformat()
    call(store,"active","session.record",{
        "domain":"sports","account_id":"one","state":"ACTIVE",
        "session_ref":"native_local_one","observed_at":now})
    no_obs=call(store,"route_2","context.route",payload)
    assert no_obs["next_step"]=="OBSERVE_CURRENT_FINANCIAL_STATE"
    later=datetime.now(timezone.utc).isoformat()
    call(store,"obs","observation.ingest",{
        "domain":"sports","account_id":"one","observation_id":"new_obs",
        "session_ref":"native_local_one","observed_at":later,
        "source":"DOM","origin":"example.invalid","evidence_sha256":"a"*64,
        "fields":{"available_balance":"50.00"}})
    ready=call(store,"route_3","context.route",payload)
    assert ready["state"]=="READY"
    assert ready["native_browser_handoff"]["kind"]=="PLACE_BET"
    assert ready["order_or_bet_submitted"] is False
    assert store.verify_audit()==3


def test_contract_schema_and_registered_operations_match():
    from wolf_app.store import ALL_OPERATIONS
    from pathlib import Path
    file=Path(__file__).resolve().parents[1]/"contracts/wolf-app-bridge-v1.schema.json"
    document=json.loads(file.read_text())
    assert "context.route" in ALL_OPERATIONS
    assert set(document["properties"]["operation"]["enum"])==ALL_OPERATIONS


def test_browser_goals_do_not_take_raw_credentials_or_js_and_do_not_execute():
    r=route_context(goal="TYPE_TEXT",account=None,capabilities=["TYPE"],
                    permissions=["INTERACT"],target="search_field")
    assert r["native_browser_handoff"]=={
        "kind":"TYPE","target_id":"search_field",
        "requires_current_site_state":True,
    }
    assert "password" not in json.dumps(r).lower()
    assert r["browser_action_executed"] is False


def test_database_financial_intent_handoff_and_receipt(tmp_path):
    store=ApplicationStore(tmp_path/"wolf.sqlite3")
    call(store,"reg","account.register",{
        "domain":"sports","account_id":"acct","platform_id":"site",
        "currency":"ZMW","display_name":"Test"})
    goal={"domain":"sports","account_id":"acct","decision_id":"decision1",
          "observation_id":"obs1","instrument":"fixture",
          "action_kind":"PLACE_BET","proposed_amount":"1.50",
          "browser_capabilities":["PLACE_BET"],
          "platform_permissions":["TRANSACT"],"money_budget":"3.00",
          "target_id":"offer_1"}
    recovery=call(store,"before_auth","decision.propose",goal)
    assert recovery["status"]=="CONTEXT_STEP_REQUIRED"
    assert recovery["selected_next_step"]=="RESTORE_AUTHENTICATED_SESSION"
    now=datetime.now(timezone.utc).isoformat()
    call(store,"active","session.record",{
        "domain":"sports","account_id":"acct","state":"ACTIVE",
        "session_ref":"native_tab","observed_at":now})
    missing=call(store,"before_observation","decision.propose",goal)
    assert missing["selected_next_step"]=="OBSERVE_CURRENT_FINANCIAL_STATE"
    call(store,"obs","observation.ingest",{
        "domain":"sports","account_id":"acct","observation_id":"obs1",
        "session_ref":"native_tab","observed_at":datetime.now(timezone.utc).isoformat(),
        "source":"DOM","origin":"example.invalid","evidence_sha256":"a"*64,
        "fields":{"available_balance":"50.00"}})
    candidate=call(store,"ready","decision.propose",goal)
    assert candidate["status"]=="BROWSER_HANDOFF_READY"
    assert candidate["native_workflow_ready"] is True
    assert candidate["context_selection"]["state"]=="READY"
    assert candidate["context_selection"]["native_browser_handoff"]["kind"]=="PLACE_BET"
    assert candidate["browser_action_executed"] is False
    assert candidate["requires_platform_result_and_reconciliation"] is True
    receipt=call(store,"reported","decision.receipt",{
        "domain":"sports","account_id":"acct","decision_id":"decision1",
        "outcome":"NATIVE_REPORTED_SUBMITTED","result_ref":"receipt_1",
        "receipt_evidence_sha256":"b"*64})
    assert receipt["status"]=="AWAITING_PLATFORM_RECONCILIATION"
    assert receipt["requires_authoritative_platform_readback"]
    assert receipt["browser_result_is_self_reported"]
    listed=call(store,"list","decisions.list",{"domain":"sports","account_id":"acct"})
    assert listed["decisions"][0]["status"]=="AWAITING_PLATFORM_RECONCILIATION"
    assert len(listed["decisions"])==1
    # No second submit under same decision identity after an ambiguous receipt.
    from wolf_app.bridge import process
    from json import dumps
    duplicated={"schema":REQUEST_SCHEMA,"request_id":"again",
       "operation":"decision.receipt","payload":{
         "domain":"sports","account_id":"acct","decision_id":"decision1",
         "outcome":"NATIVE_REPORTED_SUBMITTED","result_ref":"receipt_2",
         "receipt_evidence_sha256":"c"*64}}
    assert process(store,dumps(duplicated))["status"]=="REJECTED"
    assert store.verify_audit()==5


def test_no_blanket_restriction_on_native_exit_or_cancellation():
    for domain,goal in (("sports","CANCEL_BET"),("trading","CLOSE_POSITION")):
        route=route_context(goal=goal,account=account(domain=domain),
              capabilities=[goal],permissions=["TRANSACT"],
              target="existing_position_1")
        assert route["state"]=="READY"
        assert route["next_step"]=="HANDOFF_TO_NATIVE_FINANCIAL_WORKFLOW"
        assert route["native_browser_handoff"]["target_id"]=="existing_position_1"
        assert "requested_amount" not in route["native_browser_handoff"]


def test_financial_unknown_site_support_or_permission_suggests_next_step():
    x=route_context(goal="PLACE_TRADE",account=account(domain="trading"),
                    capabilities=[],permissions=["OBSERVE"],
                    requested_amount="1.0",money_budget="5.0")
    assert x["state"]=="DISCOVER"
    assert x["next_step"]=="INSPECT_PLATFORM_TRANSACTION_CAPABILITY"
    assert not x["global_feature_lock"]


def test_unknown_financial_evidence_freshness_requests_discovery_not_action():
    result=route_context(goal="PLACE_BET",
        account=account(freshness="UNRECOGNIZED"),
        capabilities=["PLACE_BET"],permissions=["TRANSACT"],
        target="offer_one",requested_amount="1.00",money_budget="3.00")
    assert result["next_step"]=="VERIFY_ACCOUNT_EVIDENCE_STATE"
    assert result["native_browser_handoff"] is None
    assert result["global_feature_lock"] is False


def test_money_result_cannot_self_claim_final_settlement(tmp_path):
    from wolf_app.bridge import process
    from json import dumps
    store=ApplicationStore(tmp_path/"wolf.sqlite3")
    call(store,"reg","account.register",{"domain":"trading","account_id":"acct",
        "platform_id":"broker","currency":"USD","display_name":"Trader"})
    response=process(store,dumps({"schema":REQUEST_SCHEMA,"request_id":"fake",
       "operation":"decision.receipt","payload":{
         "domain":"trading","account_id":"acct","decision_id":"unknown",
         "outcome":"SETTLED","result_ref":"fake"}}))
    assert response["status"]=="REJECTED"
    assert store.verify_audit()==1
