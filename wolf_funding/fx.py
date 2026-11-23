"""Currency-conversion readback for a future real-money broker connection.

Offline exact-Decimal reconciliation only. The module cannot obtain FX prices,
move money, or decide a fee is real from locally asserted flags.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN

from wolf_core.contracts import ContractError, money, utc_timestamp
from wolf_funding.reconcile import FundingBlocked


@dataclass(frozen=True)
class FxEvidence:
    source_id: str
    source_digest: str
    provider_id: str
    from_currency: str
    to_currency: str
    observed_at: str
    units_to_per_from: Decimal
    source_rights_confirmed: bool

    def __post_init__(self):
        from wolf_core.contracts import identifier
        identifier(self.source_id)
        identifier(self.provider_id)
        if (type(self.from_currency) is not str or type(self.to_currency) is not str
            or len(self.from_currency)!=3 or len(self.to_currency)!=3
            or not self.from_currency.isupper() or not self.to_currency.isupper()
            or self.from_currency==self.to_currency):
            raise FundingBlocked("invalid explicit currency pair")
        if {self.from_currency,self.to_currency} != {"ZMW","USD"}:
            raise FundingBlocked("only explicit ZMW/USD pilot FX rehearsals are implemented")
        utc_timestamp(self.observed_at)
        object.__setattr__(self,"units_to_per_from",money(self.units_to_per_from,positive=True))
        if len(self.source_digest)!=64 or any(c not in "0123456789abcdef" for c in self.source_digest):
            raise FundingBlocked("invalid FX evidence digest")
        if type(self.source_rights_confirmed) is not bool:
            raise FundingBlocked("FX evidence rights must be boolean")


@dataclass(frozen=True)
class FxRehearsal:
    status: str
    reason: str
    from_amount: Decimal
    to_amount: Decimal | None
    rate: Decimal | None
    fee_from: Decimal | None
    real_transfer_authorized: bool = False


def audit_fx(*, source_amount: Decimal, source_fee: Decimal,
             verified_provider_credit: Decimal,
             evidence: FxEvidence | None,
             now: datetime, provider_id: str,
             expected_from: str, expected_to: str,
             provider_account_readback_verified: bool,
             independent_quote_verified: bool,
             max_age_seconds: int = 120,
             tolerance_to: Decimal = Decimal("0.01")) -> FxRehearsal:
    """Requires an explicit, fresh signed-off rate and independent target balance.

    Every result remains an offline rehearsal and never authorizes funding.
    """
    def blocked(reason):
        return FxRehearsal("BLOCKED",reason,source_amount,None,None,None)
    if evidence is None or not provider_account_readback_verified or not independent_quote_verified:
        return blocked("independent-two-currency-proof-missing")
    if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None:
        return blocked("clock-untrusted")
    if (evidence.provider_id != provider_id or evidence.from_currency != expected_from
        or evidence.to_currency != expected_to or not evidence.source_rights_confirmed):
        return blocked("fx-identity-or-source-rights-mismatch")
    if type(max_age_seconds) is not int or not 0 < max_age_seconds <= 600:
        return blocked("invalid-freshness-policy")
    age = now.astimezone(timezone.utc) - datetime.fromisoformat(utc_timestamp(evidence.observed_at))
    if age.total_seconds() < 0 or age.total_seconds() > max_age_seconds:
        return blocked("fx-quote-stale-or-future")
    try:
        amount = money(source_amount,positive=True)
        fee = money(source_fee,nonnegative=True)
        credit = money(verified_provider_credit,nonnegative=True)
        tolerance = money(tolerance_to,nonnegative=True)
    except ContractError:
        return blocked("unqualified-currency-amount")
    if fee >= amount:
        return blocked("fee-consumes-source")
    if tolerance > Decimal("0.01"):
        return blocked("fx-tolerance-too-permissive")
    calculated=(amount-fee)*evidence.units_to_per_from
    # Compare in exact Decimal arithmetic to the provider-reported result.
    # No inference of FX rate from net credit and no implicit rounding uplift.
    quantized=calculated.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    if abs(credit-quantized)>tolerance:
        return blocked("broker-fx-credit-mismatch")
    return FxRehearsal("MATCHED_REHEARSAL_ONLY",
                       "fx-two-currency-arithmetic-verified-not-settled",
                       amount,credit,evidence.units_to_per_from,fee)
