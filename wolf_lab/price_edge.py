"""Predeclared, fee-aware sports shadow audit; strictly no live capital.

All candidate matches and outcome labels remain distinct from the source of
hypothetical quotes. A simulated or unqualified quote cannot establish a
bookmaker edge. This scorer is an engineering rehearsal, never evidence of
fills, financial returns, licensed data access or owner release authority.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import re

from wolf_markets.quote_book import QuoteBook, QuoteRefused, OUTCOMES


SCHEMA = "wolf.shadow-price-evidence.v1"
MIN_ADVANTAGE_PER_STAKE = Decimal("0.08")
MODELED_COST_FRACTION = Decimal("0.03")
FIXED_PAPER_STAKE = Decimal("0.50")
MAX_VIRTUAL_WALLET = Decimal("100")
MIN_VALIDATED_BETS = 200
OUTCOME_POS = {name: k for k, name in enumerate(OUTCOMES)}


class EdgeRefused(ValueError):
    pass


@dataclass(frozen=True)
class ShadowSelection:
    fixture_id: str
    outcome: str
    decimal_odds: Decimal
    modeled_ev_per_stake: Decimal
    fee_fraction: Decimal
    stake: Decimal


def _decimal_probability(raw) -> Decimal:
    if type(raw) not in (float, int) or not 0 < raw < 1:
        raise EdgeRefused("probability must be a finite decimal-like JSON number")
    value = Decimal(str(raw))
    if not value.is_finite() or not 0 < value < 1:
        raise EdgeRefused("nonfinite probability")
    return value


def candidates_before_results(book: QuoteBook, prediction_rows: list[dict]) -> tuple[ShadowSelection,...]:
    """No outcome/score information may be passed to selection."""
    if not isinstance(book, QuoteBook) or book.executable or book.account_verified:
        raise EdgeRefused("book cannot grant executable authority")
    indexed = defaultdict(dict)
    for q in book.quotes:
        indexed[q.fixture_id][q.outcome] = q.decimal_odds
    ids = set()
    selections = []
    for row in prediction_rows:
        if not isinstance(row, dict) or set(row) != {"id", "prior_day_features", "class_probabilities"}:
            raise EdgeRefused("untrusted input prediction schema")
        identity = row["id"]
        if type(identity) is not str or not re.fullmatch(r"\d{4}-\d\d-\d\d\|[^|]+\|[^|]+",identity):
            raise EdgeRefused("unrecognized fixture prediction ID")
        if identity in ids:
            raise EdgeRefused("duplicate fixture forecasts")
        ids.add(identity)
        if identity not in indexed:
            raise EdgeRefused("missing complete quote observations for forecast")
        forecast = row["class_probabilities"]
        if not isinstance(forecast,list) or len(forecast)!=3:
            raise EdgeRefused("incorrect 1X2 forecast shape")
        probs = [_decimal_probability(x) for x in forecast]
        if abs(sum(probs) - Decimal("1")) > Decimal("0.00000001"):
            raise EdgeRefused("forecast probabilities do not sum to one")
        ordered = [(probs[OUTCOME_POS[o]] * indexed[identity][o]
                    - Decimal(1) - MODELED_COST_FRACTION, o)
                   for o in OUTCOMES]
        expected, side = max(ordered, key=lambda x: (x[0], -OUTCOME_POS[x[1]]))
        if expected >= MIN_ADVANTAGE_PER_STAKE:
            selections.append(ShadowSelection(identity,side,indexed[identity][side],
                                             expected,MODELED_COST_FRACTION,FIXED_PAPER_STAKE))
    if len(ids) != len(indexed):
        raise EdgeRefused("quote source contains extra fixtures outside frozen prediction set")
    return tuple(selections)


def score_shadow(book: QuoteBook, prediction_rows: list[dict], final_outcomes: dict[str, str],
                 *, independent_model_verified: bool) -> dict:
    if independent_model_verified is not True:
        raise EdgeRefused("source-bound independent model verification required")
    if not isinstance(final_outcomes,dict):
        raise EdgeRefused("separate outcome evidence required")
    ids = {r["id"] for r in prediction_rows}
    if set(final_outcomes) != ids or any(v not in OUTCOMES for v in final_outcomes.values()):
        raise EdgeRefused("outcomes not exactly bound to forecast fixture identities")
    selections = candidates_before_results(book,prediction_rows)
    wallet = MAX_VIRTUAL_WALLET
    profit = Decimal("0")
    wins = 0
    max_drawdown = Decimal("0")
    peak = wallet
    for record in selections:
        matched = record.outcome == final_outcomes[record.fixture_id]
        wins += int(matched)
        cost = (record.stake * record.fee_fraction)
        delta = (record.stake * (record.decimal_odds - 1) if matched else -record.stake) - cost
        wallet += delta
        profit += delta
        if wallet > peak:
            peak = wallet
        max_drawdown = max(max_drawdown,peak-wallet)
    report = {
        "schema": SCHEMA,
        "domain": "sports",
        "market_source_sha256": book.source_sha256,
        "market_kind": book.source_kind,
        "capture_rights": book.capture_rights,
        "quoted_fixture_count":len(prediction_rows),
        "model_verified_without_trading":True,
        "independently_account_executable_prices":False,
        "modeled_cost_fraction":str(MODELED_COST_FRACTION),
        "min_advantage_fraction":str(MIN_ADVANTAGE_PER_STAKE),
        "paper_stake_ZMW":str(FIXED_PAPER_STAKE),
        "virtual_start_ZMW":str(MAX_VIRTUAL_WALLET),
        "selected_hypothetical_bets":len(selections),
        "hypothetical_wins":wins,
        "hypothetical_net_ZMW":str(profit.quantize(Decimal("0.000001"))),
        "hypothetical_close_ZMW":str(wallet.quantize(Decimal("0.000001"))),
        "hypothetical_max_drawdown_ZMW":str(max_drawdown.quantize(Decimal("0.000001"))),
        "qualified_bet_count_threshold":MIN_VALIDATED_BETS,
        "sufficient_sample_for_real_money_claim":len(selections)>=MIN_VALIDATED_BETS,
        "live_provider_api_verified":False,
        "real_money_profit_proven":False,
        "positive_ev_proven":False,
        "financial_authority":False,
        "status":"HYPOTHETICAL_RESEARCH_NOT_EXECUTABLE",
        "caveat":"Simulated/unqualified quotes; no provider fills, legal market rights, timing authority, executable prices or robust profit claim.",
    }
    return report


def synthetic_quote_template(prediction_rows:list[dict], *, observation_days:int=1)->dict:
    """Deterministic synthetic scenarios for regression tests only.

    Use no real operator branding; this is NOT a market-feed substitute.
    """
    from datetime import date,datetime,timedelta,timezone
    if observation_days != 1:
        raise EdgeRefused("fixed synthetic scenario only")
    quotes = []
    for row in prediction_rows:
        fixture_id = row["id"]
        game_day = date.fromisoformat(fixture_id.split("|")[0])
        kickoff = datetime(game_day.year,game_day.month,game_day.day,15,0,tzinfo=timezone.utc)
        observed = kickoff-timedelta(days=1)
        for outcome, odds in zip(OUTCOMES,("2.10","3.30","3.50")):
            quotes.append({
                "fixture_id":fixture_id,"outcome":outcome,
                "offered_at":observed.isoformat(),
                "starts_at":kickoff.isoformat(),
                "decimal_odds":odds,
            })
    return {
        "schema":"wolf.research-quotes.v1",
        "source_kind":"SIMULATED_ONLY",
        "capture_rights":"UNVERIFIED_RESEARCH_ONLY",
        "provider_id":"synthetic-fixture-rehearsal",
        "currency":"ZMW",
        "account_executable":False,
        "provider_account_verified":False,
        "quotes":quotes
    }
