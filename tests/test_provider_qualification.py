from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from wolf_core.contracts import AccountScope, ContractError, Domain
from wolf_funding.provider import ProviderCategory, AutomationRight, ProviderReview, assess


def review(domain=Domain.SPORTS, rights=AutomationRight.UNKNOWN):
    scope=AccountScope(domain,"pilot-a")
    return ProviderReview(
        "provider-a",scope,
        ProviderCategory.SPORTSBOOK if domain is Domain.SPORTS else ProviderCategory.MT5_BROKER,
        "api-v1",rights)


def test_unknown_sports_venue_never_funding_ready():
    a=assess(review())
    assert a.review_status=="PENDING_EXTERNAL_PROOF"
    assert "provider-automation-permission-unknown" in a.reasons
    assert not a.real_money_permitted and not a.fund_transfer_enabled
    assert a.risk_ceiling==Decimal("0.500")


def test_explicitly_prohibited_operator_is_denied_even_if_assertions_are_favorable():
    r=replace(review(rights=AutomationRight.PROHIBITED),
        jurisdiction_confirmed=True,account_kyc_verified=True,
        actual_account_readback=True,source_rights_verified=True,
        execution_interface_verifiable=True,provider_minimum_stake=Decimal("0.01"),
        all_fees_verified=True,funding_method_verified=True,
        official_terms_source="https://provider.example/terms",
        terms_reviewed_at="2026-11-23")
    a=assess(r)
    assert a.review_status=="DENIED"
    assert "provider-terms-prohibit-automation" in a.reasons
    assert not a.real_money_permitted


@pytest.mark.parametrize("rights,expected",[
    (AutomationRight.READ_ONLY,"read-only-venue-access"),
    (AutomationRight.DEMO_ONLY,"demo-venue-access-only"),
    (AutomationRight.UNKNOWN,"provider-automation-permission-unknown"),
])
def test_non_live_rights_refused(rights,expected):
    assert expected in assess(review(rights=rights)).reasons


def test_sportsbook_minimum_stake_exceeds_k100_policy():
    r=replace(review(rights=AutomationRight.LIVE_EXPLICIT),provider_minimum_stake=Decimal("1"))
    a=assess(r)
    assert "minimum-stake-exceeds-paper-sports-cap" in a.reasons
    assert not a.fund_transfer_enabled


def test_trading_minimum_lot_is_not_risk_loss_proof():
    r=replace(review(Domain.TRADING,AutomationRight.LIVE_EXPLICIT),provider_minimum_stake=Decimal("0.01"))
    a=assess(r)
    assert "broker-minimum-loss-not-proven-by-minimum-volume" in a.reasons
    assert a.risk_ceiling==Decimal("0.2500")


def test_claiming_everything_ready_still_requires_independent_release():
    r=replace(review(rights=AutomationRight.LIVE_EXPLICIT),
        jurisdiction_confirmed=True,account_kyc_verified=True,
        actual_account_readback=True,source_rights_verified=True,
        execution_interface_verifiable=True,provider_minimum_stake=Decimal("0.10"),
        all_fees_verified=True,funding_method_verified=True,
        official_terms_source="https://provider.example/terms",
        terms_reviewed_at="2026-11-23")
    a=assess(r)
    assert a.reasons==("independent-release-and-owner-signed-policy-not-proven",)
    assert not a.real_money_permitted
    assert not a.fund_transfer_enabled


def test_provider_currency_mismatch_blocks_current_initial_budget():
    r=replace(review(Domain.TRADING),provider_currency="USD")
    assert "currency-fx-bridge-not-qualified" in assess(r).reasons


@pytest.mark.parametrize("flag",[
    "jurisdiction_confirmed","account_kyc_verified","actual_account_readback",
    "source_rights_verified","execution_interface_verifiable",
    "all_fees_verified","funding_method_verified"])
def test_missing_external_evidence_blocks_provider(flag):
    r=replace(review(rights=AutomationRight.LIVE_EXPLICIT),
        jurisdiction_confirmed=True,account_kyc_verified=True,
        actual_account_readback=True,source_rights_verified=True,
        execution_interface_verifiable=True,provider_minimum_stake=Decimal("0.01"),
        all_fees_verified=True,funding_method_verified=True,
        official_terms_source="https://provider.example/terms",
        terms_reviewed_at="2026-11-23")
    r=replace(r,**{flag:False})
    assert assess(r).reasons!=("independent-release-and-owner-signed-policy-not-proven",)


def test_wrong_domains_and_invalid_rights_cannot_be_registered():
    with pytest.raises(ContractError,match="non-trading"):
        replace(review(Domain.TRADING),category=ProviderCategory.SPORTSBOOK)
    with pytest.raises(ContractError,match="permission type"):
        replace(review(),automation_right="APPROVED")
    with pytest.raises(ContractError):
        replace(review(),provider_minimum_stake=Decimal("-1"))


def test_suspended_provider_always_denied_from_release():
    r=replace(review(rights=AutomationRight.LIVE_EXPLICIT),provider_suspended=True)
    assert "provider-suspended-or-limited" in assess(r).reasons
    assert assess(r).review_status=="DENIED"
    assert not assess(r).real_money_permitted
