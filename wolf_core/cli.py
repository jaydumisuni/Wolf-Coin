"""Read-only first-light diagnosis. No daemon, execution or financial effects."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any

from .ledger import GENESIS, SCHEMA_VERSION, canonical, digest


def doctor(database: str | Path) -> dict[str, Any]:
    path = Path(database).expanduser().resolve()
    report: dict[str, Any] = {
        "schema": "wolf.doctor.v0",
        "status": "BLOCKED",
        "mode": "RESEARCH",
        "live_enabled": False,
        "execution_adapters": 0,
        "accounts": 0,
        "events": 0,
    }
    if not path.is_file():
        report["status"] = "UNINITIALIZED"
        report["reason"] = "paper-ledger-not-created"
        return report
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
            version = db.execute("SELECT value FROM ledger_meta WHERE key='schema_version'").fetchone()
            if version is None or version[0] != str(SCHEMA_VERSION):
                raise ValueError("ledger-version-mismatch")
            rows = db.execute("""SELECT stream,seq,event_id,kind,payload,occurred_at,previous,event_digest
                                 FROM events ORDER BY stream,seq""").fetchall()
            prev: dict[str, str] = {}
            seqs: dict[str, int] = {}
            for stream, seq, event_id, kind, payload, occurred_at, previous, actual_digest in rows:
                last_hash = prev.get(stream, GENESIS)
                if seq != seqs.get(stream, 0) + 1 or previous != last_hash:
                    raise ValueError("ledger-sequence-or-chain-invalid")
                if canonical(json.loads(payload)) != payload:
                    raise ValueError("noncanonical-ledger-event")
                if digest(stream, seq, event_id, kind, payload, occurred_at, previous) != actual_digest:
                    raise ValueError("ledger-hash-invalid")
                prev[stream] = actual_digest
                seqs[stream] = seq
            report.update(status="RESEARCH_ONLY", accounts=len(seqs), events=len(rows))
    except (sqlite3.DatabaseError, OSError, ValueError, KeyError, TypeError) as exc:
        report.update(status="BLOCKED", reason=type(exc).__name__)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wolf", description="Wolf-Coin safe first-light diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("doctor", help="read-only integrity and release status")
    command.add_argument("--db", required=True, type=Path, help="paper SQLite ledger path")
    args = parser.parse_args(argv)
    result = doctor(args.db)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"RESEARCH_ONLY", "UNINITIALIZED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
