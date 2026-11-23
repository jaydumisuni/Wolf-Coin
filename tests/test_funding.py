from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlite3

import pytest

from wolf_core.contracts import AccountScope, ContractError, Domain
from wolf_core.ledger import EventLedger
from wolf_funding.reconcile import (
    Direction, ExternalStatement, FundingBlocked, FundingJournal, FundingPlan,
    FundingPolicy, Status, reconcile_offline,
)

NOW=datetime(2026,11,23,10,0,tzinfo=timezone.utc)
STAMP=NOW.isoformat()


def case(domain=Domain.SPORTS, direction=Direction.DEPOSIT, gross=Decimal("100"),
         fees=Decimal("2.50"), approved=True):
    scope=AccountScope(domain,"pilot-a")
    p=FundingPlan("dep-001",scope,"provider-a",direction,gross,STAMP,approved)
    # Both observations are scoped to the same operation, but come from
    # independent model sources and have distinct evidence hashes.
    net=gross-fees
    wallet_amount=gross if direction is Direction.DEPOSIT else net
    provider_amount=net if direction is Direction.DEPOSIT else gross
    w=ExternalStatement("bank-statement","EXTERNAL_WALLET","provider-a","pilot-a",
                        domain,"ZMW","dep-001",STAMP,wallet_amount,direction,"a"*64)
    v=ExternalStatement("provider-statement","PROVIDER_ACCOUNT","provider-a","pilot-a",
                        domain,"ZMW","dep-001",STAMP,provider_amount,direction,"b"*64)
    return p,w,v


@pytest.mark.parametrize("domain",list(Domain))
@pytest.mark.parametrize("direction",list(Direction))
def test_two_source_rehearsal_reconciles_both_domains_and_directions(domain,direction):
    plan,ext,venue=case(domain,direction)
    result=reconcile_offline(plan,ext,venue,documented_customer_fees=Decimal("2.50"),
                             reference_now=NOW,independent_evidence_verified=True)
    assert result.status is Status.CONFIRMED_REHEARSAL
    assert result.gross==Decimal("100")
    assert result.net==Decimal("97.50")
    assert result.observed_cost==Decimal("2.50")
    assert result.real_funds_moved is False and result.real_funding_authorized is False


@pytest.mark.parametrize("change,reason",[
    ({"owner_approved":False},"owner-not-approved"),
    ({"gross_amount":Decimal("110")},"funding-cap-exceeded"),
])
def test_user_cap_and_approval_refusals(change,reason):
    p,e,v=case()
    if "gross_amount" in change:
        with pytest.raises(FundingBlocked, match="K100 pilot ceiling"):
            replace(p,**change)
    else:
        p=replace(p,**change)
        assert reconcile_offline(p,e,v,documented_customer_fees=Decimal("2.50"),
                                 reference_now=NOW,independent_evidence_verified=True).reason==reason


@pytest.mark.parametrize("name,params,reason",[
    ("ext_missing",{},"external-source-proof-missing"),
    ("v_missing",{},"external-source-proof-missing"),
    ("no_verification",{},"external-source-proof-missing"),
    ("same_origin",{},"not-independent-records"),
    ("same_hash",{},"not-independent-records"),
    ("wrong_provider",{},"provider-or-account-mismatch"),
    ("wrong_domain",{},"provider-or-account-mismatch"),
    ("wrong_account",{},"provider-or-account-mismatch"),
    ("wrong_ref",{},"funding-reference-mismatch"),
    ("stale",{},"statement-expired-or-future"),
    ("future",{},"statement-expired-or-future"),
    ("unexpected_provider_amount",{},"transfer-arithmetic-unreconciled"),
    ("unexpected_wallet_amount",{},"gross-not-as-planned"),
    ("unknown_fee",{},"fees-not-verifiable"),
    ("wrong_fee",{},"transfer-arithmetic-unreconciled"),
    ("wrong_roles",{},"statement-source-roles-invalid"),
])
def test_fail_closed_funding_reconciliation(name,params,reason):
    p,e,v=case()
    verify=True
    fees=Decimal("2.50")
    if name=="ext_missing":e=None
    elif name=="v_missing":v=None
    elif name=="no_verification":verify=False
    elif name=="same_origin":v=replace(v,source_id=e.source_id)
    elif name=="same_hash":v=replace(v,source_digest=e.source_digest)
    elif name=="wrong_provider":v=replace(v,provider_id="imposter")
    elif name=="wrong_domain":v=replace(v,domain=Domain.TRADING)
    elif name=="wrong_account":v=replace(v,account_id="other")
    elif name=="wrong_ref":v=replace(v,reference="other")
    elif name=="stale":v=replace(v,observed_at=(NOW-timedelta(hours=2)).isoformat())
    elif name=="future":v=replace(v,observed_at=(NOW+timedelta(seconds=1)).isoformat())
    elif name=="unexpected_provider_amount":v=replace(v,transfer_amount=Decimal("98"))
    elif name=="unexpected_wallet_amount":e=replace(e,transfer_amount=Decimal("99"))
    elif name=="unknown_fee":fees=None
    elif name=="wrong_fee":fees=Decimal("1")
    elif name=="wrong_roles":v=replace(v,source_kind="EXTERNAL_WALLET")
    result=reconcile_offline(p,e,v,documented_customer_fees=fees,reference_now=NOW,
                             independent_evidence_verified=verify)
    assert result.status is Status.PLANNED and result.reason==reason
    assert result.real_funding_authorized is False


def test_money_not_implicitly_reduced_by_operator_levy():
    p,e,v=case(fees=Decimal("0"))
    r=reconcile_offline(p,e,v,documented_customer_fees=Decimal("0"),
                        reference_now=NOW,independent_evidence_verified=True)
    assert r.net==Decimal("100")  # never assume 5% taken from customer's wallet


def test_money_fee_must_be_recorded_and_conserved():
    p,e,v=case(fees=Decimal("5"))
    r=reconcile_offline(p,e,v,documented_customer_fees=Decimal("5"),
                        reference_now=NOW,independent_evidence_verified=True)
    assert r.net==Decimal("95")
    assert r.real_funding_authorized is False


@pytest.mark.parametrize("invalid",[
    {"gross_amount":Decimal("101")},
    {"gross_amount":Decimal("NaN")},
    {"gross_amount":0.5},
    {"scope":AccountScope(Domain.SPORTS,"pilot-a","USD")},
])
def test_invalid_cross_currency_or_oversized_plans_cannot_be_created(invalid):
    p,_,_=case()
    with pytest.raises((ContractError, FundingBlocked)):
        replace(p,**invalid)


def test_policy_reduction_allowed_but_risk_increase_not():
    assert FundingPolicy(sports_ceiling=Decimal("50")).ceiling(Domain.SPORTS)==Decimal("50")
    with pytest.raises(FundingBlocked):
        FundingPolicy(trading_ceiling=Decimal("100.01"))


def test_journal_only_records_unsigned_rehearsal_proposals(tmp_path):
    j=FundingJournal(EventLedger(tmp_path/"fund.sqlite3"))
    p,_,_=case(approved=False)
    first=j.plan(p)
    assert first["mode"]=="OFFLINE_REHEARSAL"
    assert j.plan(p)==first
    assert len(j.plans(p.scope))==1
    with pytest.raises(FundingBlocked,match="conflicting"):
        j.plan(replace(p,gross_amount=Decimal("99")))
    with pytest.raises(FundingBlocked,match="owner approval"):
        j.plan(replace(p,owner_approved=True))


def test_separate_domains_do_not_share_funding_records(tmp_path):
    j=FundingJournal(EventLedger(tmp_path/"fund.sqlite3"))
    sports,_,_=case(Domain.SPORTS,approved=False)
    trading,_,_=case(Domain.TRADING,approved=False)
    j.plan(sports)
    assert j.plans(trading.scope)=={}
    j.plan(trading)
    assert len(j.plans(sports.scope))==len(j.plans(trading.scope))==1


def test_replayed_funding_journal_rejects_foreign_kinds_even_with_valid_hash(tmp_path):
    j=FundingJournal(EventLedger(tmp_path/"fund.sqlite3"))
    p,_,_=case(approved=False)
    s=j._scope(p.scope)
    j.ledger.append(s,expected_seq=0,event_id="bad-event",kind="stake_reserve",
                    payload={"source":"bogus"})
    with pytest.raises(FundingBlocked):
        j.plans(p.scope)


def test_negative_or_forged_statements_refused():
    p,e,v=case()
    with pytest.raises(ContractError):
        replace(e,transfer_amount=Decimal("-1"))
    with pytest.raises(FundingBlocked):
        replace(v,source_digest="not-hash")
    with pytest.raises(FundingBlocked):
        replace(e,currency="USD")

def test_multiple_pending_deposits_do_not_reset_account_pilot_cap(tmp_path):
    j=FundingJournal(EventLedger(tmp_path/"fund.sqlite3"))
    first,_,_=case(approved=False,gross=Decimal("70"))
    assert j.plan(first)["gross_amount"]=="70"
    with pytest.raises(FundingBlocked,match="aggregate planned deposits"):
        j.plan(replace(first,plan_id="dep-002",gross_amount=Decimal("31")))
    assert len(j.plans(first.scope))==1
    assert j.plan(replace(first,plan_id="dep-003",gross_amount=Decimal("30")))["gross_amount"]=="30"
    assert len(j.plans(first.scope))==2


def test_replayed_owner_approval_injected_into_hash_valid_ledger_is_rejected(tmp_path):
    j=FundingJournal(EventLedger(tmp_path/"fund.sqlite3"))
    p,_,_=case(approved=True)
    st=j._scope(p.scope)
    j.ledger.append(st,expected_seq=0,event_id=p.plan_id,
                    kind="funding_plan",payload=p.payload())
    with pytest.raises(FundingBlocked,match="externally unauthorized"):
        j.plans(p.scope)
