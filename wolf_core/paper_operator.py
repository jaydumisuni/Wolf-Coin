"""Interactive paper-only operator commands; never connects to a financial venue.

All capital is explicitly virtual. This CLI cannot create live effects, unfreeze
accounts, elevate a research result, or claim a calibrated market prediction.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .bankroll import PaperBankroll
from .contracts import AccountScope, ContractError, Domain, money
from .ledger import EventLedger
from wolf_sports.odds import ThreeWayQuote


def run(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wolf-paper", description="Wolf-Coin virtual funds only")
    p.add_argument("--db", type=Path, required=True, help="dedicated paper-only SQLite database")
    p.add_argument("--domain", choices=["sports", "trading"], default="sports")
    p.add_argument("--account", default="pilot-1")
    subs = p.add_subparsers(dest="operation", required=True)

    subs.add_parser("init", help="create an empty virtual account")
    subs.add_parser("status", help="show the current virtual account")

    dep = subs.add_parser("deposit", help="add VIRTUAL funds, not a real deposit")
    dep.add_argument("--amount", required=True)
    dep.add_argument("--event-id", required=True)

    withdraw = subs.add_parser("withdraw", help="subtract VIRTUAL funds")
    withdraw.add_argument("--amount", required=True)
    withdraw.add_argument("--event-id", required=True)

    freeze = subs.add_parser("freeze", help="irreversibly freeze or halt this paper account")
    freeze.add_argument("--status", required=True, choices=["FROZEN", "HALT"])
    freeze.add_argument("--event-id", required=True)

    odds = subs.add_parser("odds", help="analyze quoted 1X2 odds; never suggest placement")
    odds.add_argument("--home", required=True)
    odds.add_argument("--draw", required=True)
    odds.add_argument("--away", required=True)

    args = p.parse_args(argv)
    out = {"mode": "PAPER", "live_enabled": False, "real_money_effects": False}
    try:
        if args.operation == "odds":
            from datetime import datetime, timezone
            quote = ThreeWayQuote(
                "manual-research-only", "unverified-fixture", "1x2",
                datetime.now(timezone.utc).isoformat(),
                {"home": money(args.home, positive=True),
                 "draw": money(args.draw, positive=True),
                 "away": money(args.away, positive=True)},
                source_rights_confirmed=False,
            )
            out.update(
                status="RESEARCH_ONLY", source_rights_confirmed=False,
                provider="manual-research-only", overround=str(quote.overround),
                implied_no_vig={k: str(v) for k, v in quote.no_vig_probabilities().items()},
                verdict="NO_EXECUTION",
            )
        else:
            scope = AccountScope(Domain(args.domain), args.account)
            if args.operation == "status" and not args.db.is_file():
                raise ContractError("virtual account not initialized")
            book = PaperBankroll(EventLedger(args.db))
            if args.operation == "init":
                state = book.create(scope)
            elif args.operation == "status":
                state = book.state(scope)
            elif args.operation == "deposit":
                state = book.add_paper_funds(scope, amount=args.amount, event_id=args.event_id)
            elif args.operation == "withdraw":
                state = book.withdraw_paper_funds(scope, amount=args.amount, event_id=args.event_id)
            elif args.operation == "freeze":
                state = book.freeze(scope, event_id=args.event_id, status=args.status)
            else:
                raise ContractError("unsupported operation")
            out.update(
                status="PAPER_ONLY", domain=scope.domain.value, account=scope.account_id,
                currency=scope.currency, sequence=state.seq, account_status=state.status,
                virtual_balance=str(state.balance), virtual_available=str(state.available),
                virtual_reservations={k: str(v[0]) for k, v in state.reserved.items()},
                verdict="NO_LIVE_EXECUTION",
            )
        print(json.dumps(out, sort_keys=True))
        return 0
    except (ContractError, OSError, ValueError) as exc:
        out.update(status="BLOCKED", error=type(exc).__name__, reason=str(exc))
        print(json.dumps(out, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
