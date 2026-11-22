from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3

import pytest

from wolf_core.bankroll import FundsError, PaperBankroll
from wolf_core.contracts import AccountScope, ContractError, Domain, money, utc_timestamp
from wolf_core.ledger import EventLedger, LedgerConflict, LedgerCorruption
from wolf_guard.paper import PaperStakePolicy, review_stake
from wolf_sports.odds import ThreeWayQuote, expected_return_per_unit


def accounts(tmp_path: Path):
    db = EventLedger(tmp_path / "paper.db")
    book = PaperBankroll(db)
    s = AccountScope(Domain.SPORTS, "sports-1")
    t = AccountScope(Domain.TRADING, "trading-1")
    book.create(s)
    book.create(t)
    return db, book, s, t


def quote(now=None, rights=True):
    now = now or datetime(2026, 11, 23, tzinfo=timezone.utc)
    return ThreeWayQuote("licensed-demo", "fixture-42", "market-1", now.isoformat(),
                         {"home": Decimal("1.70"), "draw": Decimal("4.10"),
                          "away": Decimal("5.50")}, rights)


def test_wallet_isolation_and_conservation_after_paper_settlement(tmp_path):
    ledger, book, sports, trading = accounts(tmp_path)
    book.add_paper_funds(sports, amount="100", event_id="s-deposit")
    book.add_paper_funds(trading, amount="100", event_id="t-deposit")
    b = book.post(sports, event_id="s-reserve", kind="stake_reserve",
                  payload={"stake_id": "ticket-1", "amount": "0.50", "odds": "1.70"})
    assert b.balance == Decimal("100")
    assert b.available == Decimal("99.50")
    assert book.state(trading).balance == Decimal("100")
    assert book.post(sports, event_id="s-settle", kind="stake_settle",
                     payload={"stake_id": "ticket-1", "result": "WIN", "payout": "0.850"}).balance == Decimal("100.350")
    assert book.state(sports).available == Decimal("100.350")
    assert book.state(trading).balance == Decimal("100")
    assert ledger.events(sports)[-1].seq == 4
    assert ledger.events(trading)[-1].seq == 2


def test_duplicate_event_retries_are_idempotent_and_conflicts_refused(tmp_path):
    ledger, book, sports, _ = accounts(tmp_path)
    book.add_paper_funds(sports, amount="100", event_id="dep-one")
    assert book.add_paper_funds(sports, amount="100", event_id="dep-one").balance == 100
    with pytest.raises(LedgerConflict):
        book.add_paper_funds(sports, amount="900", event_id="dep-one")
    assert len(ledger.events(sports)) == 2


def test_stale_revision_and_integrity_corruption_rejected(tmp_path):
    ledger, book, sports, _ = accounts(tmp_path)
    e = ledger.events(sports)
    assert e[0].seq == 1
    with pytest.raises(LedgerConflict):
        ledger.append(sports, expected_seq=0, event_id="bad", kind="funds_add",
                      payload={"amount": "5"})
    book.add_paper_funds(sports, amount="100", event_id="dep")
    with sqlite3.connect(ledger.database) as db:
        db.execute("UPDATE events SET payload=? WHERE stream=? AND seq=2",
                   ('{"amount":"100000"}', sports.stream))
    with pytest.raises(LedgerCorruption):
        book.state(sports)


def test_concurrent_fenced_append_exactly_one_wins(tmp_path):
    ledger, _, sports, _ = accounts(tmp_path)
    def append(i):
        try:
            ledger.append(sports, expected_seq=1, event_id=f"parallel-{i}",
                          kind="funds_add", payload={"amount": "1"})
            return "appended"
        except LedgerConflict:
            return "stale"
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(append, range(8)))
    assert results.count("appended") == 1
    assert results.count("stale") == 7
    assert len(ledger.events(sports)) == 2


def test_frozen_account_can_settle_outstanding_but_not_new_risk(tmp_path):
    _, book, sports, _ = accounts(tmp_path)
    book.add_paper_funds(sports, amount="100", event_id="dep")
    book.post(sports, event_id="reserve", kind="stake_reserve",
              payload={"stake_id": "ticket", "amount": "0.5", "odds": "2"})
    book.freeze(sports, event_id="freeze")
    with pytest.raises(FundsError):
        book.post(sports, event_id="reserve-2", kind="stake_reserve",
                  payload={"stake_id": "ticket-2", "amount": "0.5", "odds": "2"})
    assert book.post(sports, event_id="settle", kind="stake_settle",
                     payload={"stake_id": "ticket", "result": "VOID", "payout": "0.5"}).balance == 100
    assert book.state(sports).status == "FROZEN"


def test_account_currency_binding_and_replayed_wallet(tmp_path):
    ledger, book, sports, _ = accounts(tmp_path)
    book.add_paper_funds(sports, amount="100", event_id="dep")
    again = PaperBankroll(EventLedger(ledger.database))
    assert again.state(sports).balance == 100
    wrong = AccountScope(Domain.SPORTS, sports.account_id, "USD")
    with pytest.raises(FundsError):
        again.create(wrong)
    with pytest.raises(FundsError):
        again.state(wrong)


def test_withdrawal_cannot_spend_reserved_stake(tmp_path):
    _, book, sports, trading = accounts(tmp_path)
    book.add_paper_funds(sports, amount="100", event_id="dep")
    book.post(sports, event_id="reserve", kind="stake_reserve",
              payload={"stake_id": "ticket", "amount": "0.5", "odds": "2"})
    with pytest.raises(FundsError):
        book.withdraw_paper_funds(sports, amount="99.6", event_id="bad-withdraw")
    assert book.withdraw_paper_funds(sports, amount="99.5", event_id="withdraw").available == 0
    with pytest.raises(FundsError):
        book.post(trading, event_id="invalid-ticket", kind="stake_reserve",
                  payload={"stake_id": "ticket", "amount": "1", "odds": "2"})


def test_trading_paper_pnl_cannot_use_sports_account(tmp_path):
    _, book, sports, trading = accounts(tmp_path)
    book.add_paper_funds(trading, amount="100", event_id="dep")
    balance = book.post(trading, event_id="close-1", kind="trade_realize",
                        payload={"trade_id": "closed-1", "pnl": "-2.5"}).balance
    assert balance == Decimal("97.5")
    with pytest.raises(FundsError):
        book.post(trading, event_id="close-duplicate", kind="trade_realize",
                  payload={"trade_id": "closed-1", "pnl": "3"})
    with pytest.raises(FundsError):
        book.post(sports, event_id="bad-trade", kind="trade_realize",
                  payload={"trade_id": "closed-1", "pnl": "3"})


def test_quote_requires_three_outcomes_and_uses_true_overround():
    q = quote()
    fair = q.no_vig_probabilities()
    assert abs(sum(fair.values()) - Decimal(1)) < Decimal("1e-25")
    assert q.overround > 1
    assert expected_return_per_unit(quote=q, selection="home",
                                    forecast_probability=Decimal("0.65")) == Decimal("0.105")
    with pytest.raises(ContractError):
        ThreeWayQuote("demo", "f1", "m1", datetime.now(timezone.utc).isoformat(),
                      {"home": Decimal("2"), "away": Decimal("3")}, True)
    with pytest.raises(ContractError):
        expected_return_per_unit(quote=q, selection="home", forecast_probability=Decimal("1.2"))


def test_paper_stake_refuses_missing_evidence_stale_and_minimum(tmp_path):
    _, book, sports, trading = accounts(tmp_path)
    book.add_paper_funds(sports, amount="100", event_id="dep")
    book.add_paper_funds(trading, amount="100", event_id="dep")
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    base = {"account": book.state(sports), "quote": quote(now), "selection": "home",
            "forecast_probability": Decimal("0.65"), "independently_calibrated": True,
            "provider_minimum": Decimal("0.5"), "now": now}
    good = review_stake(**base)
    assert (good.verdict, good.maximum_stake, good.expected_return) == ("PAPER_ELIGIBLE", Decimal("0.5"), Decimal("0.105"))
    checks = [
        ({"independently_calibrated": False}, "forecast-not-qualified"),
        ({"quote": quote(now, rights=False)}, "source-rights-unverified"),
        ({"now": now + timedelta(minutes=3)}, "quote-stale-or-in-future"),
        ({"provider_minimum": Decimal("1")}, "provider-minimum-exceeds-risk-cap"),
        ({"forecast_probability": Decimal("0.40")}, "no-supported-positive-ev"),
        ({"account": book.state(trading)}, "wrong-domain"),
    ]
    for args, why in checks:
        verdict = review_stake(**(base | args))
        assert (verdict.verdict, verdict.reason) == ("ABSTAIN", why)
    book.freeze(sports, event_id="freeze")
    assert review_stake(**(base | {"account": book.state(sports)})).reason == "account-not-active"


def test_invalid_contracts_and_no_real_money_interfaces(tmp_path):
    assert money("0.50") == Decimal("0.50")
    for val in (0.5, "NaN", "Infinity"):
        with pytest.raises(ContractError):
            money(val)
    with pytest.raises(ContractError):
        utc_timestamp("2026-11-23T00:00:00")
    with pytest.raises(ContractError):
        AccountScope(Domain.SPORTS, "bad/slash")
    with pytest.raises(ContractError):
        EventLedger(":memory:")
    assert not hasattr(PaperBankroll, "place_live_bet")
    assert not hasattr(PaperBankroll, "submit_order")


def test_unqualified_reactivation_and_halt_downgrade_are_rejected(tmp_path):
    _, book, sports, _ = accounts(tmp_path)
    book.freeze(sports, event_id="halt", status="HALT")
    with pytest.raises(FundsError):
        book.freeze(sports, event_id="unsafe-reactivate", status="ACTIVE")
    with pytest.raises(FundsError):
        book.freeze(sports, event_id="unsafe-downgrade", status="FROZEN")
    assert book.state(sports).status == "HALT"


def test_canonical_payload_rejects_float_and_different_money_amounts(tmp_path):
    ledger, book, sports, _ = accounts(tmp_path)
    with pytest.raises(ContractError):
        ledger.append(sports, expected_seq=1, event_id="float-payload", kind="funds_add",
                      payload={"amount": 0.5})
    with pytest.raises(FundsError):
        book.post(sports, event_id="zero-stake", kind="stake_reserve",
                  payload={"stake_id": "ticket", "amount": "0", "odds": "1.5"})
    assert len(ledger.events(sports)) == 1


def test_split_stakes_do_not_reset_account_risk_allowance(tmp_path):
    _, book, sports, _ = accounts(tmp_path)
    book.add_paper_funds(sports, amount="100", event_id="dep")
    book.post(sports, event_id="one", kind="stake_reserve",
              payload={"stake_id": "ticket-one", "amount": "0.3", "odds": "2"})
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    decision = review_stake(account=book.state(sports), quote=quote(now), selection="home",
                            forecast_probability=Decimal("0.65"), independently_calibrated=True,
                            provider_minimum=Decimal("0.25"), now=now)
    assert (decision.verdict, decision.reason) == ("ABSTAIN", "provider-minimum-exceeds-risk-cap")
    with pytest.raises(FundsError):
        book.post(sports, event_id="two", kind="stake_reserve",
                  payload={"stake_id": "ticket-two", "amount": "0.3", "odds": "2"})
    assert book.state(sports).available == Decimal("99.7")


def test_immutable_market_quote_after_validation():
    prices = {"home": Decimal("2"), "draw": Decimal("3.5"), "away": Decimal("4")}
    q = ThreeWayQuote("demo", "f1", "m1", datetime.now(timezone.utc).isoformat(), prices, True)
    prices["home"] = Decimal("1.05")
    assert q.prices["home"] == Decimal("2")
    with pytest.raises(TypeError):
        q.prices["home"] = Decimal("9")


def test_paper_policy_cannot_exceed_ledger_hard_cap():
    with pytest.raises(ContractError):
        PaperStakePolicy(max_fraction=Decimal("0.02"))
