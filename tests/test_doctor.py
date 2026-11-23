from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from wolf_core.bankroll import PaperBankroll
from wolf_core.cli import doctor, main
from wolf_core.contracts import AccountScope, Domain
from wolf_core.ledger import EventLedger


def test_uninitialized_doctor_is_read_only(tmp_path: Path, capsys):
    path = tmp_path / "missing.db"
    assert doctor(path)["status"] == "UNINITIALIZED"
    assert not path.exists()
    assert main(["doctor", "--db", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["live_enabled"] is False
    assert not path.exists()


def test_doctor_integrity_proof_does_not_mutate(tmp_path: Path):
    path = tmp_path / "paper.db"
    ledger = EventLedger(path)
    book = PaperBankroll(ledger)
    scope = AccountScope(Domain.SPORTS, "one")
    book.create(scope)
    book.add_paper_funds(scope, amount="100", event_id="deposit")
    raw = path.read_bytes()
    report = doctor(path)
    assert report == {"schema": "wolf.doctor.v0", "status": "RESEARCH_ONLY",
                      "mode": "RESEARCH", "live_enabled": False,
                      "execution_adapters": 0, "accounts": 1, "events": 2}
    assert path.read_bytes() == raw


def test_doctor_detects_corrupt_chain_and_malformed_db(tmp_path: Path, capsys):
    path = tmp_path / "paper.db"
    ledger = EventLedger(path)
    scope = AccountScope(Domain.SPORTS, "one")
    PaperBankroll(ledger).create(scope)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE events SET event_digest=? WHERE stream=?", ("deadbeef", scope.stream))
    assert doctor(path)["status"] == "BLOCKED"
    assert main(["doctor", "--db", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"
    corrupt = tmp_path / "not-a-db"
    corrupt.write_text("not SQLite")
    assert doctor(corrupt)["status"] == "BLOCKED"
