"""Deterministic paper-only scheduler, reusing Wolf-Coin's guarded journal.

Feeds are SIMULATED_ONLY and are never promoted to licensed provider facts.
Any ambiguous paper effect stays UNKNOWN after restart. There is no network
broker/sportsbook adapter, account credential, live mode, or money movement.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json

from wolf_core.contracts import AccountScope, Domain
from wolf_core.ledger import EventLedger
from wolf_execution.guard import Intent, ProviderSnapshot, MarketSnapshot
from wolf_execution.journal import EffectBlocked,IntentJournal,PaperVenue
from wolf_lab.price_edge import candidates_before_results
from wolf_markets.quote_book import QuoteBook


def _safe_intent_id(fixt: str, market_source_sha256: str) -> str:
    return "sim." + sha256((market_source_sha256 + ":" + fixt).encode("utf-8")).hexdigest()[:32]


def run_synthetic_cycle(db: Path, book: QuoteBook, prediction_rows: list[dict],
                        *, failure: str="none") -> dict:
    """Single bounded cycle, never a daemon or unrestricted background agent."""
    if type(book) is not QuoteBook or book.source_kind!="SIMULATED_ONLY" or book.executable:
        raise EffectBlocked("paper cycle accepts only internal synthetic quote evidence")
    if not isinstance(db, Path) or db.is_symlink():
        raise EffectBlocked("invalid/symlink paper research database")
    selections = candidates_before_results(book,prediction_rows)
    scope = AccountScope(Domain.SPORTS,"synthetic_rehearsal")
    venue = PaperVenue(provider_id="synthetic_simulator",scope=scope,failure=failure)
    journal = IntentJournal(EventLedger(db))
    statuses=[]
    examined=0
    for item in selections:
        examined+=1
        quote = next(q for q in book.quotes
                     if q.fixture_id==item.fixture_id and q.outcome==item.outcome)
        # This is a LOCAL fantasy-time in-process simulator. PaperVenue and
        # MarketSnapshot booleans mean "the simulator is self-consistent", not
        # that real bookmakers, source rights, or funding have been verified.
        now = quote.offered_at + timedelta(seconds=1)
        evidence=book.source_sha256
        name=_safe_intent_id(item.fixture_id,book.source_sha256)
        instrument="sim." + sha256(item.fixture_id.encode()).hexdigest()[:20]
        intent=Intent(
            name,scope,"synthetic_simulator",instrument,
            "research.typed.cc0.v1",evidence,
            Decimal("0.20"),Decimal("0.21"),"PAPER"
        )
        provider=ProviderSnapshot(
            scope,"synthetic_simulator",now.isoformat(),
            Decimal("100"),Decimal("0"),Decimal("0"),Decimal("0"),Decimal("0"),
            Decimal("0.10"),Decimal("0.01"),0,
            True,True,True,True,False)
        market=MarketSnapshot(instrument,quote.offered_at.isoformat(),evidence,
                              True,True,True,True)
        current=journal.propose(intent)
        if current.state!="PROPOSED":
            statuses.append({"intent_id":name,"state":current.state,
                             "simulated_submit_attempted":False})
            if current.state in ("ACCEPTED","UNKNOWN"):
                break  # Do not propose further intents across restarts.
            continue
        try:
            status=journal.dispatch_once(intent=intent,provider=provider,
                         market=market,now=now,adapter=venue)
        except EffectBlocked:
            statuses.append({"intent_id":name,"state":"BLOCKED_BY_EXISTING_OPEN_EFFECT",
                             "simulated_submit_attempted":False})
            continue
        statuses.append({"intent_id":name,"state":status.state,
                         "simulated_submit_attempted":True})
        # Prevent a process that sees an accepted/unknown/open effect from
        # silently creating another. Reconciliation requires readback.
        if status.state in ("UNKNOWN","ACCEPTED"):
            break
    return {
        "schema":"wolf.synthetic-paper-cycle.v1",
        "status":"SIMULATION_ONLY_NOT_REAL_EXECUTION",
        "quoted_fixture_count":len(prediction_rows),
        "qualified_model_profitability":False,
        "candidate_paper_selections":len(selections),
        "attempted_simulated_dispatches":venue.submit_calls,
        "examined_selections":examined,
        "durable_states":statuses,
        "money_accounts_touched":False,
        "live_venue_integrations":0,
        "synthetic_self_consistency_only":True,
        "provider_terms_or_market_data_qualified":False,
        "live_admission":False,
    }
