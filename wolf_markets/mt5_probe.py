"""Strictly read-only MT5 inspection seam for a future Windows demo lane.

Requires a deliberately supplied MT5 module/terminal. Never calls order_send,
order_check, login or symbol_select. No background startup or credentials are
created by this file. A real host/venue account is NOT yet qualified.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from wolf_core.contracts import ContractError, money


class MT5InspectionBlocked(ContractError):
    pass


@dataclass(frozen=True)
class MT5ReadOnlySnapshot:
    login: int
    server: str
    currency: str
    trade_mode: int
    balance: Decimal
    equity: Decimal
    orders: int
    positions: int
    connected: bool
    live_effects_enabled: bool = False


def inspect_demo(mt5, *, expected_login: int, expected_server: str,
                 expected_currency: str) -> MT5ReadOnlySnapshot:
    """Reads existing terminal state; requires an exact DEMO account binding."""
    if type(expected_login) is not int or expected_login <= 0:
        raise MT5InspectionBlocked("operator must supply exact login")
    if not expected_server or type(expected_server) is not str:
        raise MT5InspectionBlocked("operator must supply exact server")
    if (type(expected_currency) is not str or len(expected_currency) != 3
        or not expected_currency.isupper() or not expected_currency.isalpha()):
        raise MT5InspectionBlocked("operator must supply exact account currency")
    # Do not initialize by passing a stored password or cause a login to a
    # different account. Only inspect the terminal's CURRENT connection.
    try:
        if not bool(mt5.initialize()):
            raise MT5InspectionBlocked("MT5 terminal initialization unavailable")
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise MT5InspectionBlocked("terminal or account readback unavailable")
        if not bool(getattr(terminal, "connected", False)):
            raise MT5InspectionBlocked("terminal reports disconnected")
        if (getattr(account, "login", None) != expected_login
            or getattr(account, "server", None) != expected_server
            or getattr(account, "currency", None) != expected_currency):
            raise MT5InspectionBlocked("broker account identity mismatch")
        # The official MQL5 account enum uses 0 for a DEMO account.
        # This inspection seam rejects REAL (2) or CONTEST (1) accounts.
        if getattr(account, "trade_mode", None) != 0:
            raise MT5InspectionBlocked("only DEMO account inspections admitted")
        orders = mt5.orders_get()
        positions = mt5.positions_get()
        if orders is None or positions is None:
            raise MT5InspectionBlocked("orders or positions readback unavailable")
        balance = money(str(getattr(account, "balance", "")), nonnegative=True)
        equity = money(str(getattr(account, "equity", "")), nonnegative=True)
        return MT5ReadOnlySnapshot(expected_login, expected_server, expected_currency, 0,
                                   balance, equity, len(orders), len(positions), True)
    finally:
        # If initialization fails it may have allocated local resources;
        # shutdown is safe for this inspect-only candidate.
        mt5.shutdown()
