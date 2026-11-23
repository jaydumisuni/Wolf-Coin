"""Offline sports quote-envelope contract; never a provider/API adapter.

This is an evidence importer for *previously supplied* quote observations.
An unverified/illustrative quote must never be upgraded by a local flag into
an executable market. No network, credentials, payments or wagering calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re


SCHEMA = "wolf.research-quotes.v1"
MAX_BYTES = 2_000_000
MAX_QUOTES = 1200
PERMITTED_KINDS = ("SIMULATED_ONLY", "EXTERNAL_UNQUALIFIED")
OUTCOMES = ("H", "D", "A")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.|:-]{0,159}\Z")
# Match identities originate from pinned CC0 normalized team names; spaces
# and ampersands are valid in names, but not in provider identities.
FIXTURE_ID = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\|[a-z0-9][a-z0-9 .&'_-]{0,90}\|[a-z0-9][a-z0-9 .&'_-]{0,90}\Z")


class QuoteRefused(ValueError):
    pass


def _no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise QuoteRefused("duplicate JSON key")
        out[k] = v
    return out


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise QuoteRefused("quote timestamps must be strings")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise QuoteRefused("invalid timestamp") from e
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise QuoteRefused("quote timestamps must be explicitly UTC")
    return dt.astimezone(timezone.utc)


def _decimal(text: str) -> Decimal:
    if type(text) is not str or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,8})?", text):
        raise QuoteRefused("decimal odds must be canonical strings")
    try:
        value = Decimal(text)
    except InvalidOperation as e:
        raise QuoteRefused("invalid decimal odds") from e
    if not Decimal("1.000001") <= value <= Decimal("1000"):
        raise QuoteRefused("decimal odds outside bounded range")
    return value


@dataclass(frozen=True)
class Quote:
    fixture_id: str
    outcome: str
    offered_at: datetime
    starts_at: datetime
    decimal_odds: Decimal

    def __post_init__(self):
        if not isinstance(self.fixture_id, str) or not FIXTURE_ID.fullmatch(self.fixture_id):
            raise QuoteRefused("invalid fixture identity")
        if self.outcome not in OUTCOMES:
            raise QuoteRefused("invalid 1X2 outcome")
        if self.offered_at >= self.starts_at:
            raise QuoteRefused("cannot use odds captured at/after kickoff")
        if self.starts_at - self.offered_at > timedelta(days=30):
            raise QuoteRefused("quote is too far from scheduled kickoff")
        if not Decimal("1.000001") <= self.decimal_odds <= Decimal("1000"):
            raise QuoteRefused("invalid price")


@dataclass(frozen=True)
class QuoteBook:
    source_sha256: str
    source_kind: str
    capture_rights: str
    provider_id: str
    quotes: tuple[Quote, ...]
    executable: bool = False
    account_verified: bool = False


def load_quote_book(path: Path, *, expected_sha256: str) -> QuoteBook:
    if not isinstance(expected_sha256, str) or not HEX64.fullmatch(expected_sha256):
        raise QuoteRefused("independent source SHA-256 required")
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_BYTES:
        raise QuoteRefused("unavailable or oversized source")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected_sha256:
        raise QuoteRefused("source bytes do not match pinned SHA-256")
    try:
        record = json.loads(raw.decode("utf-8"),
                            parse_constant=lambda _: (_ for _ in ()).throw(QuoteRefused("nonfinite JSON")),
                            object_pairs_hook=_no_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError, TypeError) as e:
        raise QuoteRefused("malformed JSON quote envelope") from e
    if not isinstance(record, dict) or set(record) != {
        "schema", "source_kind", "capture_rights", "provider_id", "currency",
        "account_executable", "provider_account_verified", "quotes",
    }:
        raise QuoteRefused("unexpected quote-envelope schema")
    if record["schema"] != SCHEMA:
        raise QuoteRefused("unsupported quote schema")
    if record["source_kind"] not in PERMITTED_KINDS:
        raise QuoteRefused("only offline/unqualified research evidence accepted")
    if record["capture_rights"] != "UNVERIFIED_RESEARCH_ONLY":
        raise QuoteRefused("cannot self-certify data rights through an input file")
    if record["account_executable"] is not False or record["provider_account_verified"] is not False:
        raise QuoteRefused("quote source cannot create executable-account authority")
    if record["currency"] != "ZMW":
        raise QuoteRefused("unqualified currency bridge")
    provider_id = record["provider_id"]
    if not isinstance(provider_id, str) or not ID.fullmatch(provider_id):
        raise QuoteRefused("invalid source/provider identifier")
    items = record["quotes"]
    if not isinstance(items, list) or not 3 <= len(items) <= MAX_QUOTES:
        raise QuoteRefused("invalid quote count")
    quotes = []
    grouped = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != {
            "fixture_id", "outcome", "offered_at", "starts_at", "decimal_odds",
        }:
            raise QuoteRefused("unexpected quote record")
        quote = Quote(
            fixture_id=item["fixture_id"],
            outcome=item["outcome"],
            offered_at=_utc(item["offered_at"]),
            starts_at=_utc(item["starts_at"]),
            decimal_odds=_decimal(item["decimal_odds"]),
        )
        key = quote.fixture_id
        seen = grouped.setdefault(key, {})
        if quote.outcome in seen:
            raise QuoteRefused("duplicate outcome in fixture")
        seen[quote.outcome] = quote
        quotes.append(quote)
    for fixture_id, outcomes in grouped.items():
        if set(outcomes) != set(OUTCOMES):
            raise QuoteRefused("incomplete 1X2 fixture quotes")
        observations = {(x.offered_at, x.starts_at) for x in outcomes.values()}
        if len(observations) != 1:
            raise QuoteRefused("fixture quotes have incompatible capture/kickoff identity")
        total = sum((Decimal(1) / x.decimal_odds for x in outcomes.values()), Decimal(0))
        if not Decimal("0.75") <= total <= Decimal("1.50"):
            raise QuoteRefused("implausible complete-market overround")
    return QuoteBook(expected_sha256, record["source_kind"], record["capture_rights"],
                     provider_id, tuple(quotes))


def quote_book_summary(book: QuoteBook) -> dict:
    if not isinstance(book, QuoteBook):
        raise QuoteRefused("unqualified quote book")
    return {
        "schema": "wolf.quote-ingress-audit.v1",
        "source_sha256": book.source_sha256,
        "source_kind": book.source_kind,
        "capture_rights": book.capture_rights,
        "provider_id": book.provider_id,
        "fixture_count": len(book.quotes)//3,
        "outcome_quote_count": len(book.quotes),
        "quote_time_checked": True,
        "kickoff_leakage_rejected": True,
        "verified_provider_permission": False,
        "verified_account_executable_odds": False,
        "live_execution_allowed": False,
        "profitability_proven": False,
        "status": "OFFLINE_RESEARCH_INPUT_ONLY",
    }
