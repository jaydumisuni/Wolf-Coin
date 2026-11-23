"""Scoped paper money balances, not real deposits, broker balances or payment rails."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .contracts import AccountScope, ContractError, Domain, identifier, money
from .ledger import EventLedger, LedgerConflict


class FundsError(ContractError):
    pass


@dataclass
class AccountState:
    scope: AccountScope
    seq: int = 0
    balance: Decimal = Decimal("0")
    reserved: dict[str, tuple[Decimal, Decimal]] = field(default_factory=dict)
    used_stakes: set[str] = field(default_factory=set)
    used_trades: set[str] = field(default_factory=set)
    status: str = "ACTIVE"

    @property
    def available(self) -> Decimal:
        return self.balance - sum((v[0] for v in self.reserved.values()), Decimal("0"))


class PaperBankroll:
    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def create(self, scope: AccountScope) -> AccountState:
        prior = self.ledger.events(scope)
        if prior:
            state = self.state(scope)
            return state
        try:
            self.ledger.append(scope, expected_seq=0, event_id="account-open",
                               kind="account_open", payload={"currency": scope.currency, "mode": "PAPER"})
        except LedgerConflict:
            # A concurrent create won; read it and enforce the exact currency.
            pass
        return self.state(scope)

    @staticmethod
    def _transition(state: AccountState, kind: str, payload: dict) -> None:
        if kind == "account_open":
            if state.seq or payload != {"currency": state.scope.currency, "mode": "PAPER"}:
                raise FundsError("invalid account opening or account currency mismatch")
        elif kind == "funds_add":
            state.balance += money(payload["amount"], positive=True)
        elif kind == "funds_withdraw":
            amount = money(payload["amount"], positive=True)
            if amount > state.available:
                raise FundsError("withdrawal exceeds available paper balance")
            state.balance -= amount
        elif kind == "status_set":
            if payload["status"] not in {"FROZEN", "HALT"}:
                raise FundsError("status recovery requires separately authorized owner process")
            if state.status == "HALT" and payload["status"] != "HALT":
                raise FundsError("HALT cannot be weakened through paper status transition")
            state.status = payload["status"]
        elif kind == "stake_reserve":
            if state.scope.domain is not Domain.SPORTS:
                raise FundsError("sports stakes cannot be drawn from trading account")
            if state.status != "ACTIVE":
                raise FundsError("paper account not accepting new exposure")
            stake_id = identifier(payload["stake_id"])
            stake = money(payload["amount"], positive=True)
            odds = money(payload["odds"], positive=True)
            if odds <= 1 or stake_id in state.used_stakes or stake > state.available:
                raise FundsError("stake identity, price or bankroll check failed")
            # Paper-only hard ceiling. Evaluating separate tickets cannot reset
            # the same account's aggregate risk allowance.
            outstanding = sum((value[0] for value in state.reserved.values()), Decimal("0"))
            if outstanding + stake > state.balance * Decimal("0.005"):
                raise FundsError("aggregate paper sports exposure exceeds 0.5% of balance")
            state.reserved[stake_id] = (stake, odds)
            state.used_stakes.add(stake_id)
        elif kind == "stake_settle":
            stake_id = identifier(payload["stake_id"])
            if stake_id not in state.reserved:
                raise FundsError("missing or already settled stake")
            stake, odds = state.reserved.pop(stake_id)
            payout = money(payload["payout"], nonnegative=True)
            result = payload["result"]
            if result not in {"WIN", "LOSS", "VOID", "CASHOUT"}:
                raise FundsError("unsupported settlement result")
            if (result == "WIN" and payout != stake * odds) or (result == "LOSS" and payout != 0) or (result == "VOID" and payout != stake) or (result == "CASHOUT" and payout > stake * odds):
                raise FundsError("payout contradicts paper settlement contract")
            state.balance += payout - stake
        elif kind == "trade_realize":
            if state.scope.domain is not Domain.TRADING:
                raise FundsError("trading result cannot modify sports account")
            trade_id = identifier(payload["trade_id"])
            pnl = money(payload["pnl"])
            if trade_id in state.used_trades or state.balance + pnl < 0:
                raise FundsError("duplicate trade or unsupported negative-equity condition")
            state.used_trades.add(trade_id)
            state.balance += pnl
        else:
            raise FundsError(f"unsupported paper money event: {kind}")
        if state.balance < 0 or state.available < 0:
            raise FundsError("insufficient funds / negative paper balance")

    def state(self, scope: AccountScope) -> AccountState:
        events = self.ledger.events(scope, verify=True)
        if not events:
            raise FundsError("paper account does not exist")
        state = AccountState(scope)
        for event in events:
            try:
                self._transition(state, event.kind, event.payload)
            except (KeyError, TypeError, ContractError) as exc:
                raise FundsError(f"invalid paper event at seq {event.seq}") from exc
            state.seq = event.seq
        return state

    def post(self, scope: AccountScope, *, event_id: str, kind: str, payload: dict) -> AccountState:
        state = self.state(scope)
        existing = {e.event_id: e for e in self.ledger.events(scope)}.get(event_id)
        if existing is not None:
            # Match only the original operation, never reapply its financial effect.
            if existing.kind != kind or existing.payload != payload:
                raise LedgerConflict("paper event id reused for different financial effect")
            return state
        # Prevalidate on an isolated replay; no write unless checks succeed.
        proposed = AccountState(scope, state.seq, state.balance,
                                dict(state.reserved), set(state.used_stakes),
                                set(state.used_trades), state.status)
        try:
            self._transition(proposed, kind, payload)
        except FundsError:
            raise
        except (KeyError, TypeError, ContractError) as exc:
            raise FundsError("invalid paper operation") from exc
        self.ledger.append(scope, expected_seq=state.seq, event_id=event_id,
                           kind=kind, payload=payload)
        return self.state(scope)

    def add_paper_funds(self, scope: AccountScope, *, amount: str, event_id: str) -> AccountState:
        value = money(amount, positive=True)
        return self.post(scope, event_id=event_id, kind="funds_add", payload={"amount": str(value)})

    def withdraw_paper_funds(self, scope: AccountScope, *, amount: str, event_id: str) -> AccountState:
        value = money(amount, positive=True)
        return self.post(scope, event_id=event_id, kind="funds_withdraw", payload={"amount": str(value)})

    def freeze(self, scope: AccountScope, *, event_id: str, status: str = "FROZEN") -> AccountState:
        return self.post(scope, event_id=event_id, kind="status_set", payload={"status": status})
