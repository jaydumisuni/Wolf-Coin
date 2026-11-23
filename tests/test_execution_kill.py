"""Physical Linux process-kill proof for a paper-only dispatch in flight."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import multiprocessing
from pathlib import Path
import sys
import time

import pytest

from wolf_core.contracts import AccountScope, Domain
from wolf_core.ledger import EventLedger
from wolf_execution.guard import Intent, MarketSnapshot, ProviderSnapshot
from wolf_execution.journal import EffectBlocked, IntentJournal, PaperVenue

NOW=datetime(2026,11,23,9,0,tzinfo=timezone.utc)
SHA="a"*64


def _child(db: str, ready) -> None:
    scope=AccountScope(Domain.SPORTS,"kill-proof")
    i=Intent("kill-case",scope,"sandbox","fixture-1","strategy-v1",SHA,Decimal("0.50"),Decimal("0.25"))
    p=ProviderSnapshot(scope,"sandbox",NOW.isoformat(),Decimal("100"),Decimal("0"),Decimal("0"),
                       Decimal("0"),Decimal("0"),Decimal("0.50"),Decimal("0.10"),0,True,True,True,True)
    market=MarketSnapshot("fixture-1",NOW.isoformat(),SHA,True,True,True,True)
    j=IntentJournal(EventLedger(Path(db)))
    j.propose(i)
    def simulated_provider_wait(self,intent):
        # Our parent kills this process after the journal has durably
        # recorded dispatch_started. No real external connection occurs.
        ready.set()
        time.sleep(30)
        raise AssertionError("unexpected simulator completion")
    PaperVenue.submit=simulated_provider_wait
    a=PaperVenue(provider_id="sandbox",scope=scope)
    j.dispatch_once(intent=i,provider=p,market=market,now=NOW,adapter=a)


@pytest.mark.skipif(not sys.platform.startswith("linux"),reason="requires Linux process-kill proof")
def test_real_process_termination_retains_unknown_and_refuses_resubmission(tmp_path):
    ctx=multiprocessing.get_context("fork")
    ready=ctx.Event()
    database=tmp_path/"crash.sqlite3"
    p=ctx.Process(target=_child,args=(str(database),ready))
    p.start()
    try:
        assert ready.wait(timeout=8), "child did not reach post-journal/pre-receipt boundary"
    finally:
        p.terminate()
        p.join(timeout=5)
        if p.is_alive():
            p.kill()
            p.join(timeout=5)
    assert p.exitcode is not None
    scope=AccountScope(Domain.SPORTS,"kill-proof")
    j=IntentJournal(EventLedger(database))
    assert j.state(scope,"kill-case").state=="UNKNOWN"
    assert len(j.ledger.events(j._scope(scope)))==2
    # A new simulator with no authoritative readback cannot claim that the
    # effect did not occur or resubmit it.
    fresh=PaperVenue(provider_id="sandbox",scope=scope)
    i=Intent("kill-case",scope,"sandbox","fixture-1","strategy-v1",SHA,Decimal("0.50"),Decimal("0.25"))
    assert j.reconcile_unknown(intent=i,adapter=fresh).state=="UNKNOWN"
