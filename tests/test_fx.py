from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from wolf_funding.fx import FxEvidence, audit_fx

NOW=datetime(2026,11,23,10,0,tzinfo=timezone.utc)


def quote():
    return FxEvidence("provider-quote","a"*64,"broker-a","ZMW","USD",NOW.isoformat(),
                      Decimal("0.04"),True)


def run(e=None, **overrides):
    args=dict(
        source_amount=Decimal("100"),
        source_fee=Decimal("2"),
        verified_provider_credit=Decimal("3.92"),
        evidence=quote() if e is None else e,
        now=NOW,
        provider_id="broker-a",
        expected_from="ZMW",
        expected_to="USD",
        provider_account_readback_verified=True,
        independent_quote_verified=True,
    )
    args.update(overrides)
    return audit_fx(**args)


def test_zmw_to_usd_k100_rehearsal_exact_fx_cost():
    x=run()
    assert x.status=="MATCHED_REHEARSAL_ONLY"
    assert x.to_amount==Decimal("3.92")
    assert x.real_transfer_authorized is False


def test_reverse_currency_direction_with_explicit_reverse_rate():
    e=FxEvidence("provider-quote","a"*64,"broker-a","USD","ZMW",NOW.isoformat(),
                 Decimal("25"),True)
    x=run(e,source_amount=Decimal("3.92"),source_fee=Decimal("0.02"),
          verified_provider_credit=Decimal("97.50"),expected_from="USD",expected_to="ZMW")
    assert x.status=="MATCHED_REHEARSAL_ONLY"
    assert not x.real_transfer_authorized


@pytest.mark.parametrize("change,reason",[
    ({"provider_account_readback_verified":False},"independent-two-currency-proof-missing"),
    ({"independent_quote_verified":False},"independent-two-currency-proof-missing"),
    ({"provider_id":"wrong"},"fx-identity-or-source-rights-mismatch"),
    ({"expected_from":"USD"},"fx-identity-or-source-rights-mismatch"),
    ({"expected_to":"EUR"},"fx-identity-or-source-rights-mismatch"),
    ({"verified_provider_credit":Decimal("4.00")},"broker-fx-credit-mismatch"),
    ({"source_fee":Decimal("100")},"fee-consumes-source"),
    ({"source_fee":Decimal("-1")},"unqualified-currency-amount"),
    ({"source_amount":0.50},"unqualified-currency-amount"),
    ({"max_age_seconds":0},"invalid-freshness-policy"),
    ({"tolerance_to":Decimal("1")},"fx-tolerance-too-permissive"),
    ({"now":NOW+timedelta(minutes=3)},"fx-quote-stale-or-future"),
    ({"now":NOW-timedelta(seconds=1)},"fx-quote-stale-or-future"),
    ({"now":datetime(2026,11,23)},"clock-untrusted"),
])
def test_fx_negative_controls(change,reason):
    assert run(**change).reason==reason
    assert run(**change).real_transfer_authorized is False


def test_missing_quote_blocks():
    x=audit_fx(source_amount=Decimal("100"),source_fee=Decimal("0"),
               verified_provider_credit=Decimal("4"),evidence=None,now=NOW,
               provider_id="broker-a",expected_from="ZMW",expected_to="USD",
               provider_account_readback_verified=True,independent_quote_verified=True)
    assert x.status=="BLOCKED"
    assert not x.real_transfer_authorized


def test_expired_permission_disallows_conversion():
    assert run(replace(quote(),source_rights_confirmed=False)).status=="BLOCKED"


def test_fx_rounding_is_explicit_and_bounded():
    q=replace(quote(),units_to_per_from=Decimal("0.039999"))
    assert run(q,verified_provider_credit=Decimal("3.92")).status=="MATCHED_REHEARSAL_ONLY"
    assert run(q,verified_provider_credit=Decimal("3.94")).status=="BLOCKED"

def test_other_currency_pairs_cannot_sneak_into_initial_fx_pilot():
    with pytest.raises(Exception,match="ZMW/USD"):
        FxEvidence("provider-quote","a"*64,"broker-a","EUR","USD",NOW.isoformat(),
                   Decimal("1.15"),True)
