"""Wolf-Coin's browser-to-backend contract. No website credentials in IPC.

Source of truth: Browser supplies observations, never authority. Native host
must authenticate the IPC transport separately; all browser-originated values
remain UNVERIFIED until an actual platform acceptance procedure exists.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re

from wolf_core.contracts import ContractError, utc_timestamp

BRIDGE_SCHEMA = "wolf.app.bridge.v2"
REQUEST_SCHEMA = "wolf.app.request.v1"
MAX_MESSAGE = 64_000
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\Z")
CURRENCY_PATTERN = re.compile(r"[A-Z]{3}\Z")
AMOUNT_PATTERN = re.compile(r"-?(?:0|[1-9]\d{0,14})(?:\.\d{1,6})?\Z")
MONEY_KEYS = frozenset({
    "cash_balance", "available_balance", "pending_bets", "pending_deposits",
    "pending_withdrawals", "open_exposure", "realized_pnl", "unrealized_pnl",
    "fees_total", "deposits_total", "withdrawals_total",
})
NONNEGATIVE_KEYS = MONEY_KEYS - {"realized_pnl", "unrealized_pnl"}
SESSION_STATES = frozenset({"ACTIVE", "LOGGED_OUT", "EXPIRED", "OFFLINE", "PAUSED"})
SOURCES = frozenset({"DOM", "ACCESSIBILITY", "VISIBLE_NETWORK", "SCREENSHOT"})
TRANSACTION_KINDS = frozenset({"DEPOSIT", "WITHDRAWAL", "FEE", "BET", "TRADE", "SETTLEMENT"})
TRANSACTION_STATES = frozenset({"PENDING", "SETTLED", "CANCELLED"})
FORBIDDEN_KEYS = frozenset({
    "password", "cookie", "cookies", "authorization", "auth", "bearer",
    "token", "access_token", "refresh_token", "session_cookie", "secret",
    "private_key", "api_key", "otp", "pin", "credential", "credentials",
    "localstorage", "sessionstorage", "set-cookie",
})


def obj(value, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise ContractError("object expected")
    found = set(value)
    if required - found or found - (required | optional):
        raise ContractError("unexpected or missing fields")
    return value


def ident(value: str, name: str = "identifier") -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ContractError(f"invalid {name}")
    return value


def currency(value: str) -> str:
    if not isinstance(value, str) or not CURRENCY_PATTERN.fullmatch(value):
        raise ContractError("invalid currency")
    return value


def amount(value: str, *, nonnegative: bool = False) -> str:
    if type(value) is not str or not AMOUNT_PATTERN.fullmatch(value):
        raise ContractError("amount must be a bounded canonical decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ContractError("invalid amount") from exc
    if not number.is_finite() or (nonnegative and number < 0):
        raise ContractError("out of range amount")
    return str(number)


def time(value: str, *, max_future_seconds: int = 300) -> str:
    ts = utc_timestamp(value)
    parsed = datetime.fromisoformat(ts)
    if parsed > datetime.now(timezone.utc) + timedelta(seconds=max_future_seconds):
        raise ContractError("future observation timestamp")
    return ts


def check_no_secrets(value) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str) or k.casefold().replace("-", "_") in FORBIDDEN_KEYS:
                raise ContractError("secret-bearing fields forbidden in backend IPC")
            check_no_secrets(v)
    elif isinstance(value, list):
        if len(value) > 500:
            raise ContractError("array too large")
        for item in value:
            check_no_secrets(item)


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()


def parse_request(value: dict) -> tuple[str, str, dict]:
    obj(value, {"schema", "request_id", "operation", "payload"}, {"auth_tag"})
    if "auth_tag" in value:
        tag=value["auth_tag"]
        if not isinstance(tag,str) or not re.fullmatch(r"[0-9a-f]{64}",tag):
            raise ContractError("invalid signed IPC authentication tag")
    if value["schema"] != REQUEST_SCHEMA:
        raise ContractError("unsupported request schema")
    check_no_secrets(value)
    return ident(value["request_id"], "request ID"), ident(value["operation"], "operation"), (
        value["payload"] if isinstance(value["payload"], dict) else
        (_ for _ in ()).throw(ContractError("payload must be an object"))
    )


def response(request_id: str, status: str, data: dict) -> dict:
    return {
        "schema": BRIDGE_SCHEMA, "request_id": request_id,
        "status": status, "data": data,
    }
