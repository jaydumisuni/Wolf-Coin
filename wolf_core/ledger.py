"""SQLite hash-chain paper event journal, CAS append, and independent replay.

The hash chain detects accidental changes; it is NOT an externally anchored
or tamper-proof audit log. No broker, sportsbook, secret or network access.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from .contracts import AccountScope, ContractError, identifier, utc_now, utc_timestamp


GENESIS = "0" * 64
SCHEMA_VERSION = 1


class LedgerConflict(ContractError):
    pass


class LedgerCorruption(ContractError):
    pass


def canonical(value: Any) -> str:
    def no_float(item: Any) -> None:
        if isinstance(item, float):
            raise ContractError("binary float is forbidden in ledger payload")
        if isinstance(item, dict):
            for v in item.values():
                no_float(v)
        elif isinstance(item, (list, tuple)):
            for v in item:
                no_float(v)
    no_float(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContractError("payload must be canonical JSON without floats or non-finite numbers") from exc


def digest(stream: str, seq: int, event_id: str, kind: str,
           payload: str, timestamp: str, previous: str) -> str:
    raw = canonical({"stream": stream, "seq": seq, "event_id": event_id,
                     "kind": kind, "payload": payload, "occurred_at": timestamp,
                     "previous": previous})
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Event:
    stream: str
    seq: int
    event_id: str
    kind: str
    payload: dict[str, Any]
    occurred_at: str
    previous: str
    digest: str


class EventLedger:
    def __init__(self, database: str | Path):
        self.database = str(database)
        # In-memory SQLite is intentionally not supported; durability is required.
        if self.database == ":memory:":
            raise ContractError("durable SQLite path required")
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("CREATE TABLE IF NOT EXISTS ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO ledger_meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
            row = db.execute("SELECT value FROM ledger_meta WHERE key='schema_version'").fetchone()
            if row is None or row[0] != str(SCHEMA_VERSION):
                raise LedgerCorruption("unsupported schema version")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                stream TEXT NOT NULL, seq INTEGER NOT NULL, event_id TEXT NOT NULL,
                kind TEXT NOT NULL, payload TEXT NOT NULL, occurred_at TEXT NOT NULL,
                previous TEXT NOT NULL, event_digest TEXT NOT NULL,
                PRIMARY KEY (stream, seq), UNIQUE (stream, event_id))""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, isolation_level=None, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _event(row: tuple[Any, ...]) -> Event:
        return Event(row[0], row[1], row[2], row[3], json.loads(row[4]), row[5], row[6], row[7])

    def events(self, scope: AccountScope, *, verify: bool = True) -> tuple[Event, ...]:
        stream = scope.stream
        with closing(self._connect()) as db:
            rows = db.execute("""SELECT stream, seq, event_id, kind, payload, occurred_at,
                         previous, event_digest FROM events WHERE stream=? ORDER BY seq""", (stream,)).fetchall()
        items = tuple(self._event(row) for row in rows)
        if verify:
            previous = GENESIS
            for i, event in enumerate(items, 1):
                stored_payload = rows[i - 1][4]
                if (event.seq != i or event.previous != previous or
                    canonical(event.payload) != stored_payload or
                    digest(stream, i, event.event_id, event.kind, stored_payload,
                           event.occurred_at, previous) != event.digest):
                    raise LedgerCorruption(f"integrity check failed at event {i}")
                previous = event.digest
        return items

    def append(self, scope: AccountScope, *, expected_seq: int, event_id: str,
               kind: str, payload: dict[str, Any], occurred_at: str | None = None) -> Event:
        if isinstance(expected_seq, bool) or not isinstance(expected_seq, int) or expected_seq < 0:
            raise ContractError("expected_seq must be a nonnegative integer")
        event_id = identifier(event_id)
        kind = identifier(kind)
        if not isinstance(payload, dict):
            raise ContractError("payload must be an object")
        payload_text = canonical(payload)
        timestamp = utc_timestamp(occurred_at) if occurred_at is not None else utc_now()
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing = db.execute("""SELECT stream, seq, event_id, kind, payload,
                               occurred_at, previous, event_digest FROM events
                               WHERE stream=? AND event_id=?""", (scope.stream, event_id)).fetchone()
                if existing is not None:
                    event = self._event(existing)
                    if event.kind != kind or existing[4] != payload_text or (occurred_at is not None and event.occurred_at != timestamp):
                        raise LedgerConflict("event identity reused for conflicting payload")
                    db.execute("COMMIT")
                    return event
                latest = db.execute("SELECT seq, event_digest FROM events WHERE stream=? ORDER BY seq DESC LIMIT 1",
                                    (scope.stream,)).fetchone()
                current = latest[0] if latest else 0
                if current != expected_seq:
                    raise LedgerConflict(f"stale stream revision: expected {expected_seq}, actual {current}")
                previous = latest[1] if latest else GENESIS
                event_digest = digest(scope.stream, current + 1, event_id, kind, payload_text, timestamp, previous)
                db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (scope.stream, current + 1, event_id, kind, payload_text, timestamp, previous, event_digest))
                db.execute("COMMIT")
                return Event(scope.stream, current + 1, event_id, kind, payload, timestamp, previous, event_digest)
            except Exception:
                db.execute("ROLLBACK")
                raise
