"""Strict, standard-library-only contract primitives used in paper mode."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import re


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


class ContractError(ValueError):
    """Malformed or insufficiently scoped evidence."""


class Domain(str, Enum):
    SPORTS = "sports"
    TRADING = "trading"


class Mode(str, Enum):
    RESEARCH = "RESEARCH"
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    SHADOW = "SHADOW"
    SAFE = "SAFE"
    HALT = "HALT"


@dataclass(frozen=True)
class AccountScope:
    domain: Domain
    account_id: str
    currency: str = "ZMW"

    def __post_init__(self) -> None:
        if not isinstance(self.domain, Domain):
            raise ContractError("domain must be a Domain enum")
        if not isinstance(self.account_id, str) or not _ID.fullmatch(self.account_id):
            raise ContractError("invalid account_id")
        if not isinstance(self.currency, str) or not _CURRENCY.fullmatch(self.currency):
            raise ContractError("currency must be a three-letter uppercase ISO code")

    @property
    def stream(self) -> str:
        return f"{self.domain.value}/{self.account_id}"


def money(value: str | Decimal, *, nonnegative: bool = False, positive: bool = False) -> Decimal:
    """Never infer a monetary amount through binary floating-point input."""
    if isinstance(value, bool) or not isinstance(value, (str, Decimal)):
        raise ContractError("monetary values must be Decimal or decimal strings")
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ContractError("invalid monetary value") from exc
    if not amount.is_finite() or (nonnegative and amount < 0) or (positive and amount <= 0):
        raise ContractError("non-finite or out-of-range monetary value")
    return amount


def utc_timestamp(value: str) -> str:
    if not isinstance(value, str):
        raise ContractError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError("timestamp must be timezone aware")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def identifier(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ContractError("invalid identifier")
    return value
