from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from wolf_core.contracts import AccountScope, ContractError, Domain
from wolf_core.ledger import EventLedger, LedgerConflict, LedgerCorruption
from wolf_execution.guard import GuardedPolicy, Intent, MarketSnapshot, ProviderSnapshot, preflight
from wolf_execution.journal import EffectBlocked, IntentJournal, PaperVenue, Receipt

NOW = datetime(2026,11,23,9,0,tzinfo=timezone.utc)
ST = NOW.isoformat()
SHA = "a"*64


def fixture(*, account="pilot-1", domain=Domain.SPORTS, intent_id="case-001"):
    scope = AccountScope(domain, account)
    intent = Intent(intent_id, scope, "sandbox", "market-1", "strategy-v1", SHA,
                    Decimal("0.50"), Decimal("0.25"))
    provider = ProviderSnapshot(
        scope, "sandbox", ST, Decimal("100"), Decimal("0"),
        Decimal("0"), Decimal("0"), Decimal("0"),
        Decimal("0.50"), Decimal("0.10"), 0, True, True, True, True)
    market = MarketSnapshot("market-1", ST, SHA, True, True, True, True)
    return scope, intent, provider, market


def test_guard_admits_small_paper_case_not_money():
    scope,i,p,m=fixture()
    verdict=preflight(i,p,m,now=NOW)
    assert verdict.status=="PAPER_ELIGIBLE"
    assert verdict.risk_ceiling==Decimal("0.2500")


@pytest.mark.parametrize("key,value,reason",[
    ("account_verified",False,"provider-account-unverified-or-frozen"),
    ("frozen",True,"provider-account-unverified-or-frozen"),
    ("session_valid",False,"provider-session-expired"),
    ("provider_permission_verified",False,"provider-permission-unverified"),
    ("readback_supported",False,"provider-readback-unavailable"),
    ("daily_loss",Decimal("1.00"),"daily-stop"),
    ("weekly_loss",Decimal("2.50"),"weekly-stop"),
    ("peak_drawdown",Decimal("5"),"drawdown-stop"),
    ("open_positions",2,"position-count-stop"),
    ("open_risk",Decimal("0.75"),"risk-ceiling-exceeded"),
    ("minimum_risk",Decimal("0.50"),"provider-minimum-exceeds-allowance"),
    ("minimum_notional",Decimal("1.00"),"provider-minimum-exceeds-allowance"),
])
def test_guard_provider_negative_controls(key,value,reason):
    _,i,p,m=fixture()
    assert preflight(i,replace(p,**{key:value}),m,now=NOW).reason==reason


@pytest.mark.parametrize("key,value,reason",[
    ("licensed",False,"market-evidence-unqualified"),
    ("identity_verified",False,"market-evidence-unqualified"),
    ("pricing_verified",False,"market-evidence-unqualified"),
    ("market_open",False,"market-closed"),
    ("source_digest","b"*64,"instrument-or-evidence-mismatch"),
    ("instrument_id","other-market","instrument-or-evidence-mismatch"),
])
def test_guard_market_negative_controls(key,value,reason):
    _,i,p,m=fixture()
    assert preflight(i,p,replace(m,**{key:value}),now=NOW).reason==reason


def test_guard_rejects_wrong_account_session_time_and_untrusted_clock():
    _,i,p,m=fixture()
    assert preflight(i,replace(p,scope=AccountScope(Domain.SPORTS,"other")),m,now=NOW).reason=="account-or-provider-mismatch"
    assert preflight(i,p,m,now=NOW+timedelta(seconds=31)).reason=="stale-or-future-evidence"
    assert preflight(i,p,replace(m,observed_at=(NOW+timedelta(seconds=1)).isoformat()),now=NOW).reason=="stale-or-future-evidence"
    assert preflight(i,p,m,now=datetime(2026,11,23)).reason=="clock-untrusted"


def test_unqualified_live_mode_never_constructs_a_live_intent():
    scope,i,_,_=fixture()
    with pytest.raises(ContractError,match="cannot construct live intents"):
        replace(i,mode="GUARDED_LIVE")
    with pytest.raises(ContractError,match="decimal"):
        replace(i,notional=0.5)  # float cannot pass monetary evidence
    with pytest.raises(ContractError,match="risk policy"):
        GuardedPolicy(max_trade_fraction=Decimal("0.5"))


def test_propose_replay_and_same_idempotency(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    assert j.propose(i).state=="PROPOSED"
    assert j.propose(i).state=="PROPOSED"
    with pytest.raises(EffectBlocked,match="conflicting"):
        j.propose(replace(i,notional=Decimal("0.60")))
    assert len(j.ledger.events(j._scope(s)))==1


def test_dispatch_success_no_duplicate_simulated_effect(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    a=PaperVenue(provider_id="sandbox",scope=s)
    j.propose(i)
    st=j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a)
    assert st.state=="ACCEPTED"
    assert st.receipt.reference=="paper.case-001"
    assert a.submit_calls==1
    with pytest.raises(EffectBlocked,match="never resubmit"):
        j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a)
    assert a.submit_calls==1


def test_provider_rejection_is_stable_terminal_result(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    a=PaperVenue(provider_id="sandbox",scope=s,failure="reject")
    j.propose(i)
    assert j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a).state=="REJECTED"
    with pytest.raises(EffectBlocked,match="only matching UNKNOWN"):
        j.reconcile_unknown(intent=i,adapter=a)


def test_simulated_lost_ack_before_effect_stays_unknown(tmp_path):
    s,i,p,m=fixture()
    path=tmp_path/"exec.sqlite3"
    j=IntentJournal(EventLedger(path))
    a=PaperVenue(provider_id="sandbox",scope=s,failure="before")
    j.propose(i)
    assert j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a).state=="UNKNOWN"
    assert a.submit_calls==1
    # New process uses the same SQLite event chain; never retries.
    j2=IntentJournal(EventLedger(path))
    assert j2.state(s,i.intent_id).state=="UNKNOWN"
    assert j2.reconcile_unknown(intent=i,adapter=a).state=="UNKNOWN"
    with pytest.raises(EffectBlocked,match="never resubmit"):
        j2.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a)
    assert a.submit_calls==1


def test_lost_ack_after_effect_reconciles_without_second_submit(tmp_path):
    s,i,p,m=fixture()
    path=tmp_path/"exec.sqlite3"
    j=IntentJournal(EventLedger(path))
    a=PaperVenue(provider_id="sandbox",scope=s,failure="after")
    j.propose(i)
    assert j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a).state=="UNKNOWN"
    j2=IntentJournal(EventLedger(path))
    assert j2.reconcile_unknown(intent=i,adapter=a).state=="ACCEPTED"
    assert a.submit_calls==1
    assert j2.state(s,i.intent_id).state=="ACCEPTED"


def test_unknown_blocks_entire_account_until_authoritative_reconciliation(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    a=PaperVenue(provider_id="sandbox",scope=s,failure="before")
    j.propose(i)
    j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a)
    _,next_intent,_,_=fixture(intent_id="case-002")
    j.propose(next_intent)
    with pytest.raises(EffectBlocked,match="unresolved or open effect"):
        j.dispatch_once(intent=next_intent,provider=p,market=m,now=NOW,adapter=a)


def test_account_and_domain_isolation(tmp_path):
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    s,i,p,m=fixture()
    a=PaperVenue(provider_id="sandbox",scope=s,failure="before")
    j.propose(i)
    j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a)
    t,other,op,om=fixture(domain=Domain.TRADING)
    oa=PaperVenue(provider_id="sandbox",scope=t)
    j.propose(other)
    assert j.dispatch_once(intent=other,provider=op,market=om,now=NOW,adapter=oa).state=="ACCEPTED"
    assert j.state(s,"case-001").state=="UNKNOWN"
    assert j.state(t,"case-001").state=="ACCEPTED"


def test_wrong_adapter_never_reaches_submission(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    j.propose(i)
    class Dangerous:
        mode="PAPER_SIM"
        scope=s
        provider_id="sandbox"
        def submit(self,intent):
            raise AssertionError("would be unsafe")
    with pytest.raises(EffectBlocked,match="built-in paper"):
        j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=Dangerous())
    assert j.state(s,i.intent_id).state=="PROPOSED"


def test_evidence_failure_prevents_durable_start(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    a=PaperVenue(provider_id="sandbox",scope=s)
    j.propose(i)
    with pytest.raises(EffectBlocked,match="risk veto"):
        j.dispatch_once(intent=i,provider=replace(p,account_verified=False),market=m,now=NOW,adapter=a)
    assert a.submit_calls==0
    assert j.state(s,i.intent_id).state=="PROPOSED"


def test_mismatched_readback_is_never_accepted(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    a=PaperVenue(provider_id="sandbox",scope=s,failure="after")
    j.propose(i)
    j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a)
    a.receipts[i.intent_id]=Receipt(i.intent_id,"other","ACCEPTED","paper.other",True)
    with pytest.raises(EffectBlocked,match="not authoritative"):
        j.reconcile_unknown(intent=i,adapter=a)
    assert j.state(s,i.intent_id).state=="UNKNOWN"


def test_after_crash_new_simulator_cannot_invent_readback(tmp_path):
    s,i,p,m=fixture()
    file=tmp_path/"exec.sqlite3"
    j=IntentJournal(EventLedger(file))
    a=PaperVenue(provider_id="sandbox",scope=s,failure="after")
    j.propose(i)
    j.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=a)
    # A fresh local simulator has no persisted provider proof, and cannot
    # convert missing receipt into no-execution.
    b=PaperVenue(provider_id="sandbox",scope=s)
    assert IntentJournal(EventLedger(file)).reconcile_unknown(intent=i,adapter=b).state=="UNKNOWN"


def test_broken_semantic_state_even_with_valid_hash_is_refused(tmp_path):
    s,i,p,m=fixture()
    j=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    j.propose(i)
    stream=j._scope(s)
    j.ledger.append(stream,expected_seq=1,event_id="case-001.invalid",
                    kind="dispatch_complete",
                    payload={"intent_id":i.intent_id,"provider_id":"sandbox",
                             "outcome":"ACCEPTED","reference":"paper.case-001",
                             "authoritative":True})
    with pytest.raises(EffectBlocked,match="receipt requires"):
        j.state(s,i.intent_id)


def test_replayed_hash_tampering_detected(tmp_path):
    import sqlite3
    s,i,p,m=fixture()
    file=tmp_path/"exec.sqlite3"
    j=IntentJournal(EventLedger(file))
    j.propose(i)
    with sqlite3.connect(file) as db:
        db.execute("UPDATE events SET payload='{}' WHERE kind='intent_proposed'")
    with pytest.raises(LedgerCorruption):
        j.state(s,i.intent_id)


def test_scope_suffix_too_long_is_refused(tmp_path):
    s,i,p,m=fixture(account="x"*94)
    with pytest.raises(ContractError,match="invalid identifier"):
        IntentJournal(EventLedger(tmp_path/"exec.sqlite3")).propose(i)

def test_atomic_unique_append_refuses_duplicate_dispatch_identity(tmp_path):
    s,i,p,m=fixture()
    ledger=EventLedger(tmp_path/"exec.sqlite3")
    stream=AccountScope(s.domain,"pilot-1.exec")
    ledger.append(stream,expected_seq=0,event_id="case-001.start",kind="dispatch_started",
                  payload={"intent_id":"case-001"},must_be_new=True)
    with pytest.raises(LedgerConflict,match="repeat effect"):
        ledger.append(stream,expected_seq=0,event_id="case-001.start",kind="dispatch_started",
                      payload={"intent_id":"case-001"},must_be_new=True)
    assert len(ledger.events(stream))==1


def test_accepted_paper_effect_blocks_other_exposure_until_closing_protocol(tmp_path):
    s,i,p,m=fixture()
    journal=IntentJournal(EventLedger(tmp_path/"exec.sqlite3"))
    venue=PaperVenue(provider_id="sandbox",scope=s)
    journal.propose(i)
    assert journal.dispatch_once(intent=i,provider=p,market=m,now=NOW,adapter=venue).state=="ACCEPTED"
    _,second,_,_=fixture(intent_id="case-002")
    journal.propose(second)
    with pytest.raises(EffectBlocked,match="unresolved or open effect"):
        journal.dispatch_once(intent=second,provider=p,market=m,now=NOW,adapter=venue)
    assert venue.submit_calls==1


def test_money_input_as_decimal_string_is_normalized_before_risk_math():
    s,i,p,m=fixture()
    p=replace(p,equity="100",open_risk="0.10",minimum_risk="0.10")
    policy=GuardedPolicy(max_trade_fraction="0.0025")
    assert isinstance(p.equity, Decimal)
    assert isinstance(policy.max_trade_fraction, Decimal)
    verdict=preflight(i,p,m,now=NOW,policy=policy)
    assert verdict.status=="PAPER_ELIGIBLE"


def test_ledger_idempotent_default_preserved_for_bankroll(tmp_path):
    ledger=EventLedger(tmp_path/"exec.sqlite3")
    scope=AccountScope(Domain.SPORTS,"pilot")
    kwargs={"expected_seq":0,"event_id":"open","kind":"account_open",
            "payload":{"mode":"PAPER","currency":"ZMW"}}
    a=ledger.append(scope,**kwargs)
    b=ledger.append(scope,**kwargs)
    assert a.digest==b.digest and len(ledger.events(scope))==1
