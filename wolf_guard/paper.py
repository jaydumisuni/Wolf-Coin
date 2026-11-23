"""Paper-only stake eligibility. Hard refusals, no external execution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from wolf_core.bankroll import AccountState
from wolf_core.contracts import ContractError, Domain, money, utc_timestamp
from wolf_sports.odds import ThreeWayQuote, OUTCOMES, expected_return_per_unit


@dataclass(frozen=True)
class PaperStakePolicy:
    max_fraction: Decimal = Decimal("0.005")
    max_quote_age_seconds: int = 120
    minimum_positive_ev: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not 0 < money(self.max_fraction) <= Decimal("0.005"):
            raise ContractError("max_fraction cannot exceed paper ledger's 0.5% hard ceiling")
        if isinstance(self.max_quote_age_seconds, bool) or not 0 < self.max_quote_age_seconds <= 86400:
            raise ContractError("max_quote_age_seconds outside allowed bound")
        if money(self.minimum_positive_ev, nonnegative=True) > 1:
            raise ContractError("minimum_positive_ev outside allowed bound")


@dataclass(frozen=True)
class PaperDecision:
    verdict: str
    reason: str
    maximum_stake: Decimal
    expected_return: Decimal | None = None


def review_stake(*, account: AccountState, quote: ThreeWayQuote,
                 selection: str, forecast_probability: Decimal | None,
                 independently_calibrated: bool, provider_minimum: Decimal,
                 now: datetime, policy: PaperStakePolicy = PaperStakePolicy()) -> PaperDecision:
    def block(reason: str) -> PaperDecision:
        return PaperDecision("ABSTAIN", reason, Decimal("0"))
    if account.scope.domain is not Domain.SPORTS:
        return block("wrong-domain")
    if account.status != "ACTIVE":
        return block("account-not-active")
    if not quote.source_rights_confirmed:
        return block("source-rights-unverified")
    if selection not in OUTCOMES:
        return block("unsupported-outcome")
    if now.tzinfo is None or now.utcoffset() is None:
        return block("untrusted-clock")
    observed = datetime.fromisoformat(utc_timestamp(quote.observed_at))
    current = now.astimezone(timezone.utc)
    if current < observed or current - observed > timedelta(seconds=policy.max_quote_age_seconds):
        return block("quote-stale-or-in-future")
    if not independently_calibrated or forecast_probability is None:
        return block("forecast-not-qualified")
    expected_return = expected_return_per_unit(quote=quote, selection=selection,
                                              forecast_probability=forecast_probability)
    if expected_return <= policy.minimum_positive_ev:
        return block("no-supported-positive-ev")
    provider_minimum = money(provider_minimum, positive=True)
    outstanding = account.balance - account.available
    maximum = min(account.available, max(Decimal("0"), account.balance * policy.max_fraction - outstanding))
    if maximum < provider_minimum or maximum <= 0:
        return block("provider-minimum-exceeds-risk-cap")
    return PaperDecision("PAPER_ELIGIBLE", "positive-ev-paper-only", maximum, expected_return)
