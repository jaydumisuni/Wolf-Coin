"""Execution admission contracts. All code in this generation is PAPER-ONLY.

Risk review is a pure deterministic operation. An account/market snapshot is
evidence from an adapter, never authorization to spend money. Live admission
requires a separately qualified provider and release and is not implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from wolf_core.contracts import AccountScope, ContractError, Domain, Mode, identifier, money, utc_timestamp


@dataclass(frozen=True)
class Intent:
    intent_id: str
    scope: AccountScope
    provider_id: str
    instrument_id: str
    strategy_generation: str
    evidence_digest: str
    notional: Decimal
    worst_case_loss: Decimal
    mode: str = "PAPER"

    def __post_init__(self):
        for field in (self.intent_id, self.provider_id, self.instrument_id, self.strategy_generation):
            identifier(field)
        if len(self.intent_id) > 72:
            raise ContractError("intent_id too long for durable journal events")
        if len(self.evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in self.evidence_digest):
            raise ContractError("evidence_digest must be lowercase sha256")
        if money(self.notional, positive=True) != self.notional:
            raise ContractError("invalid notional")
        if money(self.worst_case_loss, positive=True) != self.worst_case_loss:
            raise ContractError("invalid worst_case_loss")
        if self.mode != "PAPER":
            raise ContractError("this execution generation cannot construct live intents")

    def payload(self) -> dict:
        return {
            "intent_id": self.intent_id, "domain": self.scope.domain.value,
            "account_id": self.scope.account_id, "currency": self.scope.currency,
            "provider_id": self.provider_id, "instrument_id": self.instrument_id,
            "strategy_generation": self.strategy_generation,
            "evidence_digest": self.evidence_digest,
            "notional": str(self.notional), "worst_case_loss": str(self.worst_case_loss),
            "mode": self.mode
        }


@dataclass(frozen=True)
class ProviderSnapshot:
    scope: AccountScope
    provider_id: str
    observed_at: str
    equity: Decimal
    open_risk: Decimal
    daily_loss: Decimal
    weekly_loss: Decimal
    peak_drawdown: Decimal
    minimum_notional: Decimal
    minimum_risk: Decimal
    open_positions: int
    account_verified: bool
    session_valid: bool
    readback_supported: bool
    provider_permission_verified: bool
    frozen: bool = False

    def __post_init__(self):
        identifier(self.provider_id)
        utc_timestamp(self.observed_at)
        for field in ("equity", "open_risk", "daily_loss", "weekly_loss", "peak_drawdown", "minimum_notional", "minimum_risk"):
            v = money(getattr(self, field), nonnegative=True)
            object.__setattr__(self, field, v)
            if field == "equity" and v <= 0:
                raise ContractError("equity must be positive")
        if type(self.open_positions) is not int or self.open_positions < 0:
            raise ContractError("invalid open_positions")
        for b in ("account_verified", "session_valid", "readback_supported", "provider_permission_verified", "frozen"):
            if type(getattr(self, b)) is not bool:
                raise ContractError("provider evidence flags must be boolean")


@dataclass(frozen=True)
class MarketSnapshot:
    instrument_id: str
    observed_at: str
    source_digest: str
    licensed: bool
    identity_verified: bool
    market_open: bool
    pricing_verified: bool

    def __post_init__(self):
        identifier(self.instrument_id)
        utc_timestamp(self.observed_at)
        if len(self.source_digest) != 64 or any(c not in "0123456789abcdef" for c in self.source_digest):
            raise ContractError("invalid market source digest")
        for b in ("licensed", "identity_verified", "market_open", "pricing_verified"):
            if type(getattr(self, b)) is not bool:
                raise ContractError("market evidence flags must be boolean")


@dataclass(frozen=True)
class GuardedPolicy:
    max_trade_fraction: Decimal = Decimal("0.0025")
    max_open_fraction: Decimal = Decimal("0.0075")
    max_daily_loss_fraction: Decimal = Decimal("0.01")
    max_weekly_loss_fraction: Decimal = Decimal("0.025")
    max_drawdown_fraction: Decimal = Decimal("0.05")
    max_positions: int = 2
    max_age_seconds: int = 30

    def __post_init__(self):
        ceilings = {
            "max_trade_fraction": Decimal("0.0025"),
            "max_open_fraction": Decimal("0.0075"),
            "max_daily_loss_fraction": Decimal("0.01"),
            "max_weekly_loss_fraction": Decimal("0.025"),
            "max_drawdown_fraction": Decimal("0.05"),
        }
        for key, hard_max in ceilings.items():
            val = money(getattr(self, key), positive=True)
            object.__setattr__(self, key, val)
            if val > hard_max:
                raise ContractError("risk policy cannot exceed guarded-live hard ceiling: " + key)
        if type(self.max_positions) is not int or not 1 <= self.max_positions <= 2:
            raise ContractError("invalid position cap")
        if type(self.max_age_seconds) is not int or not 1 <= self.max_age_seconds <= 120:
            raise ContractError("invalid freshness cap")


@dataclass(frozen=True)
class Verdict:
    status: str
    reason: str
    risk_ceiling: Decimal = Decimal("0")


def preflight(intent: Intent, provider: ProviderSnapshot, market: MarketSnapshot,
              *, now: datetime, policy: GuardedPolicy = GuardedPolicy()) -> Verdict:
    """Return eligibility to simulate a paper effect, NEVER live authority."""
    def reject(reason: str) -> Verdict:
        return Verdict("ABSTAIN", reason)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        return reject("clock-untrusted")
    if intent.mode != "PAPER":
        return reject("live-mode-not-implemented")
    if intent.scope != provider.scope or intent.provider_id != provider.provider_id:
        return reject("account-or-provider-mismatch")
    if intent.instrument_id != market.instrument_id or intent.evidence_digest != market.source_digest:
        return reject("instrument-or-evidence-mismatch")
    if not provider.account_verified or provider.frozen:
        return reject("provider-account-unverified-or-frozen")
    if not provider.session_valid:
        return reject("provider-session-expired")
    if not provider.provider_permission_verified:
        return reject("provider-permission-unverified")
    if not provider.readback_supported:
        return reject("provider-readback-unavailable")
    if not market.licensed or not market.identity_verified or not market.pricing_verified:
        return reject("market-evidence-unqualified")
    if not market.market_open:
        return reject("market-closed")
    current = now.astimezone(timezone.utc)
    for observed in (provider.observed_at, market.observed_at):
        t = datetime.fromisoformat(utc_timestamp(observed))
        if t > current or current-t > timedelta(seconds=policy.max_age_seconds):
            return reject("stale-or-future-evidence")
    eq = provider.equity
    if provider.daily_loss >= eq * policy.max_daily_loss_fraction:
        return reject("daily-stop")
    if provider.weekly_loss >= eq * policy.max_weekly_loss_fraction:
        return reject("weekly-stop")
    if provider.peak_drawdown >= eq * policy.max_drawdown_fraction:
        return reject("drawdown-stop")
    if provider.open_positions >= policy.max_positions:
        return reject("position-count-stop")
    if intent.notional < provider.minimum_notional or intent.worst_case_loss < provider.minimum_risk:
        return reject("provider-minimum-exceeds-allowance")
    cap = min(eq * policy.max_trade_fraction, eq * policy.max_open_fraction-provider.open_risk)
    if cap <= 0 or intent.worst_case_loss > cap:
        return reject("risk-ceiling-exceeded")
    return Verdict("PAPER_ELIGIBLE", "all-paper-checks-passed", cap)
