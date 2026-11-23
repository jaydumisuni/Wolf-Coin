"""End-to-end bounded in-process paper cycle, no venue, account or funds."""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import pytest

from wolf_core.contracts import AccountScope,Domain
from wolf_core.ledger import EventLedger
from wolf_execution.journal import IntentJournal,EffectBlocked
from wolf_execution.synthetic_cycle import run_synthetic_cycle
from wolf_markets.quote_book import load_quote_book
from wolf_lab.price_edge import synthetic_quote_template


def rows(n=1):
    return [{"id":f"2026-08-{10+i:02}|home_{i}|away_{i}",
             "prior_day_features":[0.5]*10,
             "class_probabilities":[0.6,0.2,0.2]}
            for i in range(n)]


def book(tmp_path,records,kind="SIMULATED_ONLY"):
    data=synthetic_quote_template(records)
    data["source_kind"]=kind
    p=tmp_path/"source.json"
    p.write_text(json.dumps(data,sort_keys=True))
    return load_quote_book(p,expected_sha256=sha256(p.read_bytes()).hexdigest())


def test_paper_cycle_single_effect_and_restart_idempotency(tmp_path):
    signals=rows()
    source=book(tmp_path,signals)
    db=tmp_path/"journal.sqlite3"
    a=run_synthetic_cycle(db,source,signals)
    assert a["status"]=="SIMULATION_ONLY_NOT_REAL_EXECUTION"
    assert a["attempted_simulated_dispatches"]==1
    assert a["durable_states"][0]["state"]=="ACCEPTED"
    assert not a["money_accounts_touched"] and not a["live_admission"]
    assert not a["provider_terms_or_market_data_qualified"]
    restarted=run_synthetic_cycle(db,source,signals)
    assert restarted["attempted_simulated_dispatches"]==0
    assert restarted["durable_states"][0]["state"]=="ACCEPTED"
    assert restarted["durable_states"][0]["simulated_submit_attempted"] is False
    journal=IntentJournal(EventLedger(db))
    scope=AccountScope(Domain.SPORTS,"synthetic_rehearsal")
    assert len(journal.ledger.events(journal._scope(scope)))==3


@pytest.mark.parametrize("fault",["before","after"])
def test_ambiguous_simulated_acknowledgement_never_resubmits(tmp_path,fault):
    signals=rows()
    source=book(tmp_path,signals)
    db=tmp_path/"journal.sqlite3"
    first=run_synthetic_cycle(db,source,signals,failure=fault)
    assert first["durable_states"][0]["state"]=="UNKNOWN"
    assert first["attempted_simulated_dispatches"]==1
    restarted=run_synthetic_cycle(db,source,signals)
    assert restarted["attempted_simulated_dispatches"]==0
    assert restarted["durable_states"][0]["state"]=="UNKNOWN"
    journal=IntentJournal(EventLedger(db))
    scope=AccountScope(Domain.SPORTS,"synthetic_rehearsal")
    kinds=[evt.kind for evt in journal.ledger.events(journal._scope(scope))]
    assert kinds==["intent_proposed","dispatch_started","dispatch_unknown"]


def test_no_multiple_parallel_accepted_exposure(tmp_path):
    signals=rows(2)
    source=book(tmp_path,signals)
    db=tmp_path/"journal.sqlite3"
    a=run_synthetic_cycle(db,source,signals)
    assert a["candidate_paper_selections"]==2
    assert a["attempted_simulated_dispatches"]==1
    assert a["examined_selections"]==1
    assert len(a["durable_states"])==1
    journal=IntentJournal(EventLedger(db))
    scope=AccountScope(Domain.SPORTS,"synthetic_rehearsal")
    assert len(journal.ledger.events(journal._scope(scope)))==3
    rerun=run_synthetic_cycle(db,source,signals)
    assert rerun["attempted_simulated_dispatches"]==0
    assert rerun["durable_states"][0]["state"]=="ACCEPTED"
    assert len(journal.ledger.events(journal._scope(scope)))==3


def test_unverified_external_quote_cannot_trigger_even_paper_simulator(tmp_path):
    signals=rows()
    source=book(tmp_path,signals,"EXTERNAL_UNQUALIFIED")
    db=tmp_path/"journal.sqlite3"
    with pytest.raises(EffectBlocked,match="only internal synthetic"):
        run_synthetic_cycle(db,source,signals)
    assert not db.exists()


def test_no_model_selection_means_no_effects(tmp_path):
    signals=rows()
    signals[0]["class_probabilities"]=[0.33,0.33,0.34]
    doc=synthetic_quote_template(signals)
    for item,odd in zip(doc["quotes"],("2.00","3.00","3.00")):
        item["decimal_odds"]=odd
    p=tmp_path/"source.json"
    p.write_text(json.dumps(doc))
    source=load_quote_book(p,expected_sha256=sha256(p.read_bytes()).hexdigest())
    db=tmp_path/"journal.sqlite3"
    a=run_synthetic_cycle(db,source,signals)
    assert a["candidate_paper_selections"]==0
    assert a["attempted_simulated_dispatches"]==0
    assert a["durable_states"]==[]


def test_symlink_db_and_broken_symlink_refused(tmp_path):
    signals=rows()
    source=book(tmp_path,signals)
    target=tmp_path/"missing-db"
    link=tmp_path/"link"
    link.symlink_to(target)
    with pytest.raises(EffectBlocked,match="symlink"):
        run_synthetic_cycle(link,source,signals)
    assert not target.exists()


def test_bad_failure_mode_does_not_leave_execution_file(tmp_path):
    signals=rows()
    source=book(tmp_path,signals)
    db=tmp_path/"journal.sqlite3"
    with pytest.raises(Exception,match="simulation failure"):
        run_synthetic_cycle(db,source,signals,failure="live")
    assert not db.exists()
