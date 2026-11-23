"""Read-only admission inventory for eventual real-capital pilots.

This is never a grant of transaction authority. It reports independently
required gates from Tenfold's durable source snapshots and refuses to convert
an untrusted file, local status flag, or model claim into live permission.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from wolf_core.contracts import Domain

CAMPAIGN = "Wolf-Coin:P0-P12+WX0-WX10:g1"
BASE = tuple("P" + str(i) for i in range(13))
SPORTS = BASE + tuple("WX" + str(i) for i in range(11))
TRADING = BASE
RELEASE_OBLIGATIONS = (
    "provider-and-permitted-live-interface",
    "read-only-identity-and-currency-proof",
    "minimum-order-size-under-verified-risk-cap",
    "sustained-independent-demo-paper-shadow-evidence",
    "restart-and-unknown-acknowledgement-reconciliation",
    "venue-native-protective-exit-and-emergency-halt",
    "separately-approved-source-and-release-review",
    "owner-signed-final-normalized-account-and-strategy-policy",
)


def observed_tenfold_states(database: Path) -> dict[str, str]:
    if not database.is_file():
        raise ValueError("Tenfold campaign evidence database is unavailable")
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5) as conn:
        row = conn.execute("SELECT snapshot_json, revision FROM campaigns WHERE campaign_id=?",
                           (CAMPAIGN,)).fetchone()
    if row is None:
        raise ValueError("required Tenfold campaign identity unavailable")
    snapshot = json.loads(row[0])
    if snapshot.get("campaign_id") != CAMPAIGN or snapshot.get("revision") != row[1]:
        raise ValueError("Tenfold campaign snapshot identity or revision mismatch")
    states = dict(snapshot["node_states"])
    if not states or any(value not in ("authorized", "ready", "leased", "running",
                                      "review", "proven", "blocked", "failed") for value in states.values()):
        raise ValueError("unrecognized Tenfold campaign states")
    return states


def report(domain: Domain, observed: dict[str, str] | None = None) -> dict:
    if not isinstance(domain, Domain):
        raise ValueError("invalid domain")
    observed = observed or {}
    required = SPORTS if domain is Domain.SPORTS else TRADING
    earned = [gate for gate in required if observed.get(gate) == "proven"]
    remaining = [gate for gate in required if observed.get(gate) != "proven"]
    return {
        "schema": "wolf.real-money-readiness.v0",
        "domain": domain.value,
        "observed_tenfold_gate_states": {key:observed.get(key,"UNAVAILABLE") for key in required},
        "proven_gate_count": len(earned),
        "required_gate_count": len(required),
        "unproven_gates": remaining,
        "external_release_obligations": list(RELEASE_OBLIGATIONS),
        "risk_cap_ZMW_on_100_virtual_reference": "0.25",
        "real_money_permitted": False,
        "live_executor_installed": False,
        "execution_adapters": 0,
        "reason": "NO_INDEPENDENT_REAL_MONEY_RELEASE_OR_QUALIFIED_PROVIDER",
        "note": "A local gate snapshot cannot confer owner signature, venue permission or live authority.",
    }


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(prog="wolf-readiness", description="Read-only live-pilot gate audit")
    cli.add_argument("--domain", required=True, choices=["sports", "trading"])
    cli.add_argument("--tenfold-db", type=Path)
    args = cli.parse_args(argv)
    states = None
    if args.tenfold_db:
        try:
            states = observed_tenfold_states(args.tenfold_db)
        except (sqlite3.Error, ValueError, TypeError, KeyError, OSError) as exc:
            print(json.dumps({"status":"EVIDENCE_UNAVAILABLE","reason":type(exc).__name__,
                              "real_money_permitted":False}),file=sys.stderr)
            return 2
    print(json.dumps(report(Domain(args.domain), states),sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
