"""Site-neutral, mathematical evidence organization across independent mock page shapes."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import json

import pytest

from wolf_app.evidence_reasoner import interpret,SCHEMA
from wolf_app.store import ApplicationStore
from wolf_app.contracts import REQUEST_SCHEMA
from wolf_app.bridge import process


def doc(*,origin="fresh-unknown.example",fields=None,controls=None,
        opportunities=None,auth="probable_authenticated",
        account="account_one",when=None):
    o={
      "schema":SCHEMA,
      "origin":origin,
      "observed_at":when or datetime.now(timezone.utc).isoformat(),
      "evidence_sha256":"a"*64,
      "browser_auth_state":auth,
      "account_id":account,
      "currency_hint":"ZMW",
      "elements":fields if fields is not None else [],
      "controls":controls if controls is not None else [],
      "opportunities":opportunities if opportunities is not None else [],
    }
    if account is None:
        del o["account_id"]
    return o


def fixture_quote(price="2.25"):
    return {"market":"Fixture 2026-12-01 A vs B","selection":"Home",
            "kind":"bet","side":"back","quote":price,"currency":"ZMW"}


def test_generic_normalization_without_site_specific_adapter():
    report=interpret(doc(
        origin="unknown-international-site.test",
        fields=[
          {"label":"Available Funds","value":"K750.00"},
          {"label":"Pending Wagers","value":"ZMW 100.00"},
          {"label":"Net Gains","value":"60.00"},
          {"label":"Completely New Business Metric","value":"12.4"}
        ],
        controls=[{"label":"Place Bet","role":"button","target_ref":"dom_btn_3"}],
        opportunities=[fixture_quote()],
    ))
    numeric={x["semantic_type"]:x for x in report["facts"]}
    assert numeric["available_balance"]["decimal"]=="750.00"
    assert numeric["available_balance"]["currency"]=="ZMW"
    assert numeric["pending_bets"]["decimal"]=="100.00"
    assert numeric["realized_pnl"]["decimal"]=="60.00"
    assert report["controls"][0]["semantic_action"]=="PLACE_BET"
    assert report["markets"][0]["market_implied_probability"]=="0.444444"
    assert report["markets"][0]["edge_verified"] is False
    assert report["next_task"]=="EVALUATE_MARKET_WITH_MODELS"
    assert report["unclassified_count"]==1
    assert any(x["relationship"]=="MEASURES" for x in report["relationships"])
    assert report["site_specific_adapter_used"] is False
    assert report["goal_discovered_without_user_provided_goal"] is True
    assert report["native_browser_action_executed"] is False


def test_site_unknown_terms_kept_in_graph_without_unsupported_terminal():
    r=interpret(doc(
      origin="unseen-service.example",
      fields=[{"label":"Mooncake Adjustment","value":"91.220"},{"label":"Rare Metric","value":"n/a"}],
      controls=[],
      auth="unverified"))
    assert r["next_task"]=="ORGANIZE_NEW_SITE_EVIDENCE"
    assert len(r["facts"])==2
    assert r["unclassified_count"]==2
    assert r["facts"][0]["decimal"]=="91.220"
    assert r["facts"][1]["type"]=="UNKNOWN_OR_TEXT"
    assert not r["markets"]


def test_price_without_market_selection_selects_discovery_not_false_strategy():
    r=interpret(doc(fields=[
       {"label":"Decimal Odds","value":"2.25"},
       {"label":"Available Funds","value":"ZMW 10.00"}
    ]))
    assert r["next_task"]=="DISCOVER_MARKET_AND_SELECTION_IDENTITIES"
    assert not r["model_forecast_connected"]
    assert not r["market_probability_math_available"]


def test_login_and_expiry_take_precedence_over_quotes():
    for auth in ("login_required","expired"):
        r=interpret(doc(auth=auth,opportunities=[fixture_quote()]))
        assert r["next_task"]=="RESTORE_AUTHENTICATED_SESSION"


def test_offline_and_old_observations_keep_data_but_request_recovery():
    r=interpret(doc(auth="offline",fields=[{"label":"Wallet Balance","value":"20"}]))
    assert r["next_task"]=="WAIT_FOR_CONNECTIVITY"
    old=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
    r=interpret(doc(when=old,fields=[{"label":"Wallet Balance","value":"20"}]))
    assert r["next_task"]=="REFRESH_BROWSER_OBSERVATION"
    assert r["facts"][0]["decimal"]=="20"


def test_unregistered_account_and_unverified_session_are_distinct():
    field=[{"label":"Available Balance","value":"35"}]
    assert interpret(doc(fields=field,account=None))["next_task"]=="REGISTER_OR_SELECT_ACCOUNT"
    assert interpret(doc(fields=field,auth="unverified"))["next_task"]=="VERIFY_SESSION_AND_ACCOUNT"


def test_conflicting_observations_retained_and_detected():
    r=interpret(doc(fields=[
       {"label":"Available Balance","value":"100.00"},
       {"label":"Available Funds","value":"120.00"}]))
    assert r["next_task"]=="RECONCILE_CONFLICTED_FINANCIAL_STATE"
    assert len(r["conflicts"])==1
    assert len(r["facts"])==2


def test_currency_is_not_guessed_without_site_or_account_hint():
    x=doc(fields=[{"label":"Cash Balance","value":"K500.00"}])
    del x["currency_hint"]
    r=interpret(x)
    assert r["facts"][0]["decimal"]=="500.00"
    assert r["facts"][0]["currency"] is None


def test_trading_prices_not_misrepresented_as_betting_probabilities():
    r=interpret(doc(
      fields=[{"label":"Portfolio Equity","value":"USD 1000.00"}],
      opportunities=[{"market":"EURUSD","selection":"spot",
                      "kind":"trade","side":"buy","quote":"1.1","currency":"USD"}]))
    assert r["markets"][0]["market_implied_probability"] is None
    assert r["markets"][0]["edge_verified"] is False
    assert not r["market_probability_math_available"]
    assert r["next_task"]=="EVALUATE_MARKET_WITH_MODELS"


def test_secret_values_or_auth_payload_not_ingested():
    with pytest.raises(Exception):
        interpret(doc(fields=[{"label":"API Key","value":"mysecret"}]))
    with pytest.raises(Exception):
        interpret(doc(origin="example.com/login?token=secret"))
    store=ApplicationStore(__import__("tempfile").mkdtemp()+"/state.sqlite3")
    envelope={"schema":REQUEST_SCHEMA,"request_id":"bad","operation":"observation.discover",
              "payload":{"document":{**doc(), "auth":"probable_authenticated"}}}
    result=process(store,json.dumps(envelope))
    assert result["status"]=="REJECTED"


def test_signed_app_operation_discovers_task_without_preselected_goal(tmp_path):
    store=ApplicationStore(tmp_path/"native.sqlite3")
    request={
      "schema":REQUEST_SCHEMA,"request_id":"auto1","operation":"observation.discover",
      "payload":{"document":doc(fields=[{"label":"Wallet Total","value":"750"},
                                          {"label":"Net Profit Loss","value":"60"}],
                                 opportunities=[fixture_quote()])},
    }
    outcome=process(store,json.dumps(request))
    assert outcome["status"]=="OK",outcome
    assert outcome["data"]["goal_discovered_without_user_provided_goal"]
    assert outcome["data"]["next_task"]=="EVALUATE_MARKET_WITH_MODELS"
    assert outcome["data"]["facts"]
    assert outcome["data"]["markets"]
    assert outcome["schema"]=="wolf.app.bridge.v2"
    assert "live_enabled" not in outcome


def test_current_contract_matches_operation_enum():
    from wolf_app.store import ALL_OPERATIONS
    from pathlib import Path
    p=Path(__file__).resolve().parents[1]/"contracts/wolf-app-bridge-v1.schema.json"
    d=json.loads(p.read_text())
    assert set(d["properties"]["operation"]["enum"])==ALL_OPERATIONS
    assert "observation.discover" in ALL_OPERATIONS

def test_dimensionless_odds_do_not_inherit_wallet_currency():
    result=interpret(doc(fields=[{"label":"Decimal Odds","value":"2.25"}]))
    odds=[v for v in result["facts"] if v["semantic_type"]=="odds"]
    assert len(odds)==1
    assert odds[0]["decimal"]=="2.25"
    assert odds[0]["currency"] is None


def test_ambiguous_dollar_symbol_not_relabelled_as_zmw():
    r=interpret(doc(fields=[{"label":"Available Funds","value":"$100.00"}]))
    balance=next(v for v in r["facts"] if v["semantic_type"]=="available_balance")
    assert balance["decimal"]=="100.00"
    assert balance["currency"] is None
