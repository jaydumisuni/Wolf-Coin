"""KRATOS first-light PAPER resident: single owner, read-only loopback UI.

This owns no live orders, payouts, strategy execution, brokerage connection,
provider credentials, or unattended money movement. It deliberately refuses
uninitialized / invalid paper ledgers; it never creates financial state.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
from http.server import ThreadingHTTPServer

from wolf_core.cli import doctor
from wolf_core.contracts import ContractError, identifier
from wolf_gateway.dashboard import handler


class ResidentBlocked(RuntimeError):
    """Unavailable safe runtime; requires operator action."""


@contextmanager
def instance_lock(database: Path):
    """A per-ledger Linux process lock; kernel releases it after abrupt exit."""
    database = database.expanduser().resolve(strict=True)
    if not database.is_file():
        raise ResidentBlocked("paper ledger not a regular file")
    lock_path = database.parent / (database.name + ".resident.lock")
    # O_NOFOLLOW protects against replacing the local lock with a symlink.
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ResidentBlocked("another resident owns this paper ledger") from exc
        # Do not leave a stale PID as proof of current ownership; flock is authority.
        os.ftruncate(fd, 0)
        os.write(fd, (str(os.getpid()) + "\n").encode("ascii"))
        os.fsync(fd)
        yield database
    finally:
        os.close(fd)


def verify_paper_state(database: Path) -> dict:
    """Fail closed on uninitialized, mismatched or corrupted journal."""
    status = doctor(database)
    if status["status"] != "RESEARCH_ONLY":
        raise ResidentBlocked("paper ledger unavailable: " + status["status"])
    return status


def serve(database: Path, account: str, port: int,
          *, lab_reports: tuple[Path, Path] | None = None,
          forecast_report: Path | None = None,
          neural_report: Path | None = None) -> int:
    identifier(account)
    if not 1024 <= port <= 65535:
        raise ResidentBlocked("port out of allowed loopback range")
    with instance_lock(database) as path:
        verify_paper_state(path)
        with ThreadingHTTPServer(("127.0.0.1", port), handler(path, account, lab_reports=lab_reports,
                                                         forecast_report=forecast_report,
                                                         neural_report=neural_report)) as server:
            server.daemon_threads = True
            print(json.dumps({
                "status": "PAPER_RESEARCH_ONLY",
                "sports": f"http://127.0.0.1:{port}/sports",
                "trading": f"http://127.0.0.1:{port}/trading",
                "live_enabled": False,
                "background_money_execution": False,
            }, sort_keys=True), flush=True)
            try:
                server.serve_forever(poll_interval=0.2)
            except KeyboardInterrupt:
                pass
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wolf-resident", description="KRATOS paper-only owner console")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--account", default="pilot-1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--lab-first", type=Path, help="local historical 2024/25 report JSON")
    p.add_argument("--lab-walkforward", type=Path, help="local three-window report JSON")
    p.add_argument("--forecast-report", type=Path, help="read-only CPU model score comparison")
    p.add_argument("--neural-summary", type=Path, help="static CC0 neural evidence summary")
    p.add_argument("--check", action="store_true", help="verify source ledger without starting server")
    args = p.parse_args(argv)
    try:
        if args.check:
            status = verify_paper_state(args.db)
            print(json.dumps({"status": "PAPER_READY", "ledger": status["status"], "live_enabled": False}))
            return 0
        if (args.lab_first is None) != (args.lab_walkforward is None):
            raise ResidentBlocked("both local lab evidence files are required")
        lab=(args.lab_first,args.lab_walkforward) if args.lab_first is not None else None
        return serve(args.db, args.account, args.port, lab_reports=lab,
                     forecast_report=args.forecast_report,
                     neural_report=args.neural_summary)
    except (ResidentBlocked, ContractError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "live_enabled": False}), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
