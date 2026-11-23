"""Funding reconciliation for future Wolf-Coin real-capital pilots.

This module is an OFFLINE rehearsal and audit contract: no bank, sportsbook,
payment, MT5, wallet, deposit or withdrawal APIs are present. A caller-provided
evidence record is not independent verification of a real provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path

from wolf_core.contracts import AccountScope, ContractError, Domain, identifier, money, utc_timestamp
from wolf_core.ledger import EventLedger


class FundingBlocked(ContractError):
    """External financing cannot be treated as a reconciled operation."""


class Direction(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class Status(str, Enum):
    PLANNED = "PLANNED"
    CONFIRMED_REHEARSAL = "CONFIRMED_REHEARSAL"


@dataclass(frozen=True)
class FundingPolicy:
    """Pilot planning envelope, not an instruction or permission to deposit."""
    sports_ceiling: Decimal = Decimal("100")
    trading_ceiling: Decimal = Decimal("100")
    currency: str = "ZMW"

    def __post_init__(self):
        for name in ("sports_ceiling", "trading_ceiling"):
            value = money(getattr(self, name), positive=True)
            if value > Decimal("100"):
                raise FundingBlocked("pilot ceiling cannot be increased by software")
            object.__setattr__(self, name, value)
        if self.currency != "ZMW":
            raise FundingBlocked("initial pilot planning restricted to ZMW")

    def ceiling(self, domain: Domain) -> Decimal:
        if domain is Domain.SPORTS:
            return self.sports_ceiling
        if domain is Domain.TRADING:
            return self.trading_ceiling
        raise FundingBlocked("unknown domain")


@dataclass(frozen=True)
class FundingPlan:
    """Manual deposit/withdrawal proposal; has no effect-transport method."""
    plan_id: str
    scope: AccountScope
    provider_id: str
    direction: Direction
    gross_amount: Decimal
    created_at: str
    owner_approved: bool = False

    def __post_init__(self):
        identifier(self.plan_id)
        identifier(self.provider_id)
        utc_timestamp(self.created_at)
        if type(self.direction) is not Direction:
            raise FundingBlocked("unknown transfer direction")
        if self.scope.currency != "ZMW":
            raise FundingBlocked("FX and foreign currency transfers require separate admission")
        value = money(self.gross_amount, positive=True)
        object.__setattr__(self, "gross_amount", value)
        if type(self.owner_approved) is not bool:
            raise FundingBlocked("owner approval evidence invalid")
        if value > Decimal("100"):
            raise FundingBlocked("planned transfer exceeds K100 pilot ceiling")

    def payload(self):
        return {
            "plan_id": self.plan_id,
            "provider_id": self.provider_id,
            "domain": self.scope.domain.value,
            "account_id": self.scope.account_id,
            "currency": self.scope.currency,
            "direction": self.direction.value,
            "gross_amount": str(self.gross_amount),
            "created_at": self.created_at,
            "owner_approved": self.owner_approved,
            "mode": "OFFLINE_REHEARSAL",
        }


@dataclass(frozen=True)
class ExternalStatement:
    """Observed source statement, untrusted until independently verified."""
    source_id: str
    source_kind: str  # EXTERNAL_WALLET or PROVIDER_ACCOUNT
    provider_id: str
    account_id: str
    domain: Domain
    currency: str
    reference: str
    observed_at: str
    transfer_amount: Decimal
    direction: Direction
    source_digest: str

    def __post_init__(self):
        for x in (self.source_id, self.provider_id, self.account_id, self.reference):
            identifier(x)
        if self.source_kind not in ("EXTERNAL_WALLET", "PROVIDER_ACCOUNT"):
            raise FundingBlocked("unsupported statement origin")
        if self.currency != "ZMW":
            raise FundingBlocked("FX requires separate two-currency readback")
        utc_timestamp(self.observed_at)
        if type(self.domain) is not Domain or type(self.direction) is not Direction:
            raise FundingBlocked("statement scope is not typed")
        v = money(self.transfer_amount, nonnegative=True)
        object.__setattr__(self, "transfer_amount", v)
        if len(self.source_digest) != 64 or any(c not in "0123456789abcdef" for c in self.source_digest):
            raise FundingBlocked("source statement digest must be sha256")


@dataclass(frozen=True)
class FundingRehearsalResult:
    plan_id: str
    status: Status
    gross: Decimal
    net: Decimal | None
    observed_cost: Decimal | None
    reason: str
    real_funds_moved: bool = False
    real_funding_authorized: bool = False


def reconcile_offline(plan: FundingPlan, external: ExternalStatement | None,
                      provider: ExternalStatement | None, *,
                      documented_customer_fees: Decimal | None,
                      reference_now: datetime, policy: FundingPolicy = FundingPolicy(),
                      independent_evidence_verified: bool = False) -> FundingRehearsalResult:
    """Compare independent records in a disconnected fixture.

    Deliberately returns a rehearsal-only verdict, even if the caller claims
    'independent_evidence_verified' true. No external action or admission.
    """
    def reject(reason):
        return FundingRehearsalResult(plan.plan_id, Status.PLANNED, plan.gross_amount, None, None, reason)
    if plan.gross_amount > policy.ceiling(plan.scope.domain):
        return reject("funding-cap-exceeded")
    if not plan.owner_approved:
        return reject("owner-not-approved")
    if not isinstance(reference_now, datetime) or reference_now.tzinfo is None or reference_now.utcoffset() is None:
        return reject("clock-untrusted")
    if external is None or provider is None or not independent_evidence_verified:
        return reject("external-source-proof-missing")
    if external.source_kind != "EXTERNAL_WALLET" or provider.source_kind != "PROVIDER_ACCOUNT":
        return reject("statement-source-roles-invalid")
    if (external.source_id == provider.source_id or
        external.source_digest == provider.source_digest):
        return reject("not-independent-records")
    for s in (external, provider):
        if (s.provider_id != plan.provider_id or
            s.domain != plan.scope.domain or
            s.account_id != plan.scope.account_id or
            s.currency != plan.scope.currency or
            s.direction != plan.direction):
            return reject("provider-or-account-mismatch")
        if s.reference != plan.plan_id:
            return reject("funding-reference-mismatch")
        age = reference_now.astimezone(timezone.utc) - datetime.fromisoformat(utc_timestamp(s.observed_at))
        if age.total_seconds() < 0 or age.total_seconds() > 3600:
            return reject("statement-expired-or-future")
    try:
        costs = money(documented_customer_fees, nonnegative=True)
    except ContractError:
        return reject("fees-not-verifiable")
    # For a deposit, the external debit is the gross payment, the provider
    # credit is net. Withdrawal reverses which source carries gross.
    gross = external.transfer_amount if plan.direction is Direction.DEPOSIT else provider.transfer_amount
    net = provider.transfer_amount if plan.direction is Direction.DEPOSIT else external.transfer_amount
    if gross != plan.gross_amount:
        return reject("gross-not-as-planned")
    if net < 0 or net + costs != gross:
        return reject("transfer-arithmetic-unreconciled")
    return FundingRehearsalResult(plan.plan_id, Status.CONFIRMED_REHEARSAL, gross, net, costs,
                                  "two-source-arithmetic-matched-rehearsal-only")


class FundingJournal:
    """Append/replay of proposed plans. Deliberately cannot settle real funds."""
    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    @staticmethod
    def _scope(scope: AccountScope) -> AccountScope:
        return AccountScope(scope.domain, identifier(scope.account_id + ".fund"), scope.currency)

    def plans(self, scope: AccountScope) -> dict[str, dict]:
        result = {}
        for event in self.ledger.events(self._scope(scope)):
            if event.kind != "funding_plan":
                raise FundingBlocked("unrecognized funding ledger transition")
            p = event.payload
            if (p.get("mode") != "OFFLINE_REHEARSAL"
                or p.get("owner_approved") is not False
                or p.get("account_id") != scope.account_id
                or p.get("domain") != scope.domain.value
                or p.get("currency") != scope.currency):
                raise FundingBlocked("invalid or externally unauthorized funding-plan scope")
            if p.get("plan_id") in result:
                raise FundingBlocked("duplicate funding plan")
            result[p["plan_id"]] = p
        return result

    def plan(self, proposal: FundingPlan) -> dict:
        if proposal.owner_approved:
            # Owner-approved means a future final authorization that cannot be
            # established via this unsigned local journal.
            raise FundingBlocked("locally asserted owner approval cannot authorize funding")
        if proposal.gross_amount > FundingPolicy().ceiling(proposal.scope.domain):
            raise FundingBlocked("pilot funding cap exceeded")
        result = self.plans(proposal.scope)
        if proposal.plan_id in result:
            if result[proposal.plan_id] != proposal.payload():
                raise FundingBlocked("funding ID reused with conflicting payload")
            return result[proposal.plan_id]
        # Independent pending deposit intents must share ONE account-wide
        # budget; a fresh event ID must not reset the pilot limit.
        prior_deposits = sum((
            money(record["gross_amount"],positive=True)
            for record in result.values()
            if record.get("direction") == Direction.DEPOSIT.value
        ), Decimal("0"))
        if proposal.direction is Direction.DEPOSIT and (
            prior_deposits + proposal.gross_amount > FundingPolicy().ceiling(proposal.scope.domain)
        ):
            raise FundingBlocked("aggregate planned deposits exceed pilot cap")
        st = self._scope(proposal.scope)
        events = self.ledger.events(st)
        self.ledger.append(st, expected_seq=len(events), event_id=proposal.plan_id,
                           kind="funding_plan", payload=proposal.payload())
        return self.plans(proposal.scope)[proposal.plan_id]
