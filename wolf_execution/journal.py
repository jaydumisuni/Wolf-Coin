"""Durable, fail-closed paper effect lifecycle.

A dispatch-started event is durably recorded BEFORE invoking a simulator.
Any interrupted/ambiguous dispatch is UNKNOWN, never silently retried.
No real-money provider or network transport exists in this implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from wolf_core.contracts import AccountScope, ContractError, identifier
from wolf_core.ledger import EventLedger, LedgerConflict
from .guard import GuardedPolicy, Intent, MarketSnapshot, ProviderSnapshot, Verdict, preflight


class EffectBlocked(ContractError):
    """An effect or unsafe state was refused."""


@dataclass(frozen=True)
class Receipt:
    intent_id: str
    provider_id: str
    outcome: str
    reference: str
    authoritative: bool

    def __post_init__(self):
        identifier(self.intent_id)
        identifier(self.provider_id)
        identifier(self.reference)
        if self.outcome not in ("ACCEPTED", "REJECTED") or type(self.authoritative) is not bool:
            raise ContractError("invalid receipt")


@dataclass(frozen=True)
class IntentStatus:
    intent_id: str
    state: str
    payload: dict
    receipt: Receipt | None = None


class PaperVenue:
    """In-memory PAPER simulator; deliberately cannot connect to a real venue.

    Loss of simulator memory cannot be mistaken for a negative provider receipt.
    This object is explicitly unqualified for production or live execution.
    """
    mode = "PAPER_SIM"

    def __init__(self, *, provider_id: str, scope: AccountScope, failure: str = "none"):
        self.provider_id = identifier(provider_id)
        self.scope = scope
        if failure not in ("none", "before", "after", "reject"):
            raise ContractError("unknown simulation failure mode")
        self.failure = failure
        self.receipts: dict[str, Receipt] = {}
        self.submit_calls = 0

    def submit(self, intent: Intent) -> Receipt:
        if intent.scope != self.scope or intent.provider_id != self.provider_id:
            raise EffectBlocked("simulated provider account mismatch")
        self.submit_calls += 1
        if self.failure == "before":
            raise TimeoutError("simulated lost acknowledgement before effect")
        outcome = "REJECTED" if self.failure == "reject" else "ACCEPTED"
        result = Receipt(intent.intent_id, self.provider_id, outcome,
                         identifier("paper." + intent.intent_id), True)
        self.receipts[intent.intent_id] = result
        if self.failure == "after":
            raise TimeoutError("simulated lost acknowledgement after effect")
        return result

    def readback(self, intent: Intent) -> Receipt | None:
        if intent.scope != self.scope or intent.provider_id != self.provider_id:
            raise EffectBlocked("simulated readback identity mismatch")
        return self.receipts.get(intent.intent_id)


class IntentJournal:
    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    @staticmethod
    def _scope(scope: AccountScope) -> AccountScope:
        # Never mutate the paper bankroll stream. Its replay contract has
        # different event types and must remain independent.
        return AccountScope(scope.domain, identifier(scope.account_id + ".exec"), scope.currency)

    def _replay(self, scope: AccountScope) -> dict[str, IntentStatus]:
        states: dict[str, IntentStatus] = {}
        for event in self.ledger.events(self._scope(scope), verify=True):
            p = event.payload
            intent_id = identifier(p.get("intent_id", ""))
            previous = states.get(intent_id)
            if event.kind == "intent_proposed":
                if previous is not None or p.get("intent", {}).get("intent_id") != intent_id:
                    raise EffectBlocked("malformed or duplicate durable intent")
                if p["intent"].get("domain") != scope.domain.value or p["intent"].get("account_id") != scope.account_id:
                    raise EffectBlocked("durable intent account identity mismatch")
                if p["intent"].get("mode") != "PAPER":
                    raise EffectBlocked("non-paper intent found in ledger")
                states[intent_id] = IntentStatus(intent_id, "PROPOSED", p["intent"])
                continue
            if previous is None:
                raise EffectBlocked("orphan effect transition")
            if event.kind == "dispatch_started":
                if previous.state != "PROPOSED":
                    raise EffectBlocked("repeated or illegal effect transition")
                # Replaying an incomplete started effect must become UNKNOWN.
                states[intent_id] = IntentStatus(intent_id, "UNKNOWN", previous.payload)
            elif event.kind == "dispatch_unknown":
                if previous.state != "UNKNOWN":
                    raise EffectBlocked("unknown transition without durable dispatch")
            elif event.kind in ("dispatch_complete", "dispatch_reconciled"):
                if previous.state != "UNKNOWN":
                    raise EffectBlocked("receipt requires started/unknown effect")
                receipt = Receipt(p["intent_id"], p["provider_id"], p["outcome"],
                                  p["reference"], p["authoritative"])
                if not receipt.authoritative or receipt.provider_id != previous.payload["provider_id"]:
                    raise EffectBlocked("unverified or mismatched effect receipt")
                states[intent_id] = IntentStatus(intent_id, receipt.outcome, previous.payload, receipt)
            else:
                raise EffectBlocked("unknown durable execution transition")
        return states

    def state(self, scope: AccountScope, intent_id: str) -> IntentStatus:
        identifier(intent_id)
        result = self._replay(scope).get(intent_id)
        if result is None:
            raise EffectBlocked("intent not found")
        return result

    def _append(self, scope: AccountScope, intent_id: str, operation: str, kind: str, payload: dict):
        # Each transition has stable idempotency identity within its account.
        stream = self._scope(scope)
        rev = self.ledger.events(stream)
        self.ledger.append(stream, expected_seq=len(rev),
                           event_id=identifier(intent_id + "." + operation),
                           kind=kind, payload={"intent_id": intent_id, **payload},
                           must_be_new=kind != "intent_proposed")

    def propose(self, intent: Intent) -> IntentStatus:
        states = self._replay(intent.scope)
        existing = states.get(intent.intent_id)
        if existing:
            if existing.payload != intent.payload():
                raise EffectBlocked("intent ID reused with conflicting payload")
            return existing
        self._append(intent.scope, intent.intent_id, "propose", "intent_proposed",
                     {"intent": intent.payload()})
        return self.state(intent.scope, intent.intent_id)

    def dispatch_once(self, *, intent: Intent, provider: ProviderSnapshot,
                      market: MarketSnapshot, now: datetime, adapter: PaperVenue,
                      policy: GuardedPolicy = GuardedPolicy()) -> IntentStatus:
        """Exactly one PAPER simulator invocation. UNKNOWN is a durable stop."""
        if type(adapter) is not PaperVenue or adapter.mode != "PAPER_SIM":
            raise EffectBlocked("only built-in paper simulation is admitted")
        if adapter.scope != intent.scope or adapter.provider_id != intent.provider_id:
            raise EffectBlocked("adapter identity mismatch")
        states = self._replay(intent.scope)
        prior = states.get(intent.intent_id)
        if prior is None or prior.payload != intent.payload() or prior.state != "PROPOSED":
            raise EffectBlocked("effect not new or payload mismatch: never resubmit")
        if any(s.state in ("UNKNOWN", "ACCEPTED") for s in states.values()):
            # No settle/close protocol is admitted in this generation. The
            # paper simulator cannot pretend that an accepted effect is closed.
            raise EffectBlocked("account has unresolved or open effect: reconciliation required")
        review = preflight(intent, provider, market, now=now, policy=policy)
        if review.status != "PAPER_ELIGIBLE":
            raise EffectBlocked("risk veto: " + review.reason)
        self._append(intent.scope, intent.intent_id, "start", "dispatch_started",
                     {"provider_id": intent.provider_id})
        # From here a process crash, timeout or lost receipt must NOT trigger
        # another submit call. Replay sees UNKNOWN until authoritative readback.
        try:
            receipt = adapter.submit(intent)
            if (type(receipt) is not Receipt or not receipt.authoritative
                or receipt.intent_id != intent.intent_id or receipt.provider_id != intent.provider_id):
                raise EffectBlocked("unverified simulated receipt")
        except Exception:
            self._append(intent.scope, intent.intent_id, "unknown", "dispatch_unknown",
                         {"reason": "provider-response-ambiguous"})
            return self.state(intent.scope, intent.intent_id)
        self._receipt(intent.scope, receipt, "complete")
        return self.state(intent.scope, intent.intent_id)

    def _receipt(self, scope: AccountScope, receipt: Receipt, operation: str) -> None:
        self._append(scope, receipt.intent_id, operation,
                     "dispatch_complete" if operation == "complete" else "dispatch_reconciled",
                     {"provider_id": receipt.provider_id,
                      "outcome": receipt.outcome, "reference": receipt.reference,
                      "authoritative": receipt.authoritative})

    def reconcile_unknown(self, *, intent: Intent, adapter: PaperVenue) -> IntentStatus:
        if type(adapter) is not PaperVenue or adapter.mode != "PAPER_SIM":
            raise EffectBlocked("only built-in paper readback is admitted")
        status = self.state(intent.scope, intent.intent_id)
        if status.payload != intent.payload() or status.state != "UNKNOWN":
            raise EffectBlocked("only matching UNKNOWN effects can reconcile")
        result = adapter.readback(intent)
        if result is None:
            return status  # a missing receipt is NOT evidence of non-execution
        if (type(result) is not Receipt or not result.authoritative
            or result.intent_id != intent.intent_id or result.provider_id != intent.provider_id):
            raise EffectBlocked("readback was not authoritative")
        self._receipt(intent.scope, result, "reconciled")
        return self.state(intent.scope, intent.intent_id)
