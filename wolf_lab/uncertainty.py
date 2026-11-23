"""Independent match-day clustered uncertainty on hypothetical 1X2 shadow net.

Outcome-blind selection is delegated to the frozen shadow policy. This
module measures how uncertain a score is under the *already examined* sample.
Synthetic or unqualified quotes NEVER become an executable market or evidence
of positive expected value, regardless of favorable interval outcomes.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json
from random import Random

from wolf_lab.price_edge import (
    candidates_before_results, score_shadow, OUTCOMES, EdgeRefused,
)
from wolf_markets.quote_book import QuoteBook


SCHEMA = "wolf.shadow-matchday-bootstrap.v1"
REPETITIONS = 5_000
SEED = 20261123


def _quantile(values: list[Decimal], numerator: int, denominator: int) -> Decimal:
    ordered = sorted(values)
    pos = (len(ordered)-1)*numerator
    lower=pos//denominator
    remainder=pos%denominator
    upper=min(lower+1,len(ordered)-1)
    return (ordered[lower]*(denominator-remainder)+ordered[upper]*remainder)/denominator


def audit_shadow_uncertainty(
    book: QuoteBook,
    predictions: list[dict],
    final_outcomes: dict[str,str],
    *,
    independent_model_verified: bool,
) -> dict:
    prior=score_shadow(book,predictions,final_outcomes,
                       independent_model_verified=independent_model_verified)
    choices=candidates_before_results(book,predictions)
    groups:dict[str,list[Decimal]]=defaultdict(list)
    for trade in choices:
        day=trade.fixture_id.partition("|")[0]
        if not day or len(day)!=10:
            raise EdgeRefused("missing matchday identity")
        outcome=final_outcomes[trade.fixture_id]
        if outcome not in OUTCOMES:
            raise EdgeRefused("invalid outcome")
        delta = (trade.stake*(trade.decimal_odds-Decimal(1))
                 if trade.outcome==outcome else -trade.stake)
        delta-=trade.stake*trade.fee_fraction
        groups[day].append(delta)
    unique_days=sorted({str(row["id"]).partition("|")[0] for row in predictions})
    if len(unique_days)<8 or len(predictions)<30:
        raise EdgeRefused("too little independent history for clustered uncertainty")
    by_day=[sum(groups.get(day,[]),Decimal(0)) for day in unique_days]
    sample=Random(SEED)
    replicates=[]
    for _ in range(REPETITIONS):
        total=sum((by_day[sample.randrange(len(by_day))] for _ in by_day),Decimal(0))
        replicates.append(total)
    lower=_quantile(replicates,25,1000)
    upper=_quantile(replicates,975,1000)
    interval_includes_zero=lower<=0<=upper
    modeled_total=sum(by_day,Decimal(0)).quantize(Decimal("0.000001"))
    if str(modeled_total)!=prior["hypothetical_net_ZMW"]:
        raise EdgeRefused("independent matchday profits conflict with shadow report")
    return {
        "schema":SCHEMA,
        "source_kind":book.source_kind,
        "source_sha256":book.source_sha256,
        "input_prediction_fixtures":len(predictions),
        "selected_hypothetical_bets":len(choices),
        "distinct_match_days":len(by_day),
        "fixed_bootstrap_seed":SEED,
        "clustered_bootstrap_repetitions":REPETITIONS,
        "hypothetical_total_net_ZMW":str(modeled_total),
        "clustered_bootstrap_lower_95pct_ZMW":str(lower.quantize(Decimal("0.000001"))),
        "clustered_bootstrap_upper_95pct_ZMW":str(upper.quantize(Decimal("0.000001"))),
        "interval_includes_zero":interval_includes_zero,
        "previously_seen_2026_27_results":True,
        "quote_source_executable":False,
        "market_data_rights_verified":False,
        "separate_live_provider_outcomes":False,
        "profitability_proven":False,
        "venue_approval":False,
        "external_investment_or_betting_recommendation":False,
        "status":"UNCERTAINTY_RESEARCH_ONLY",
        "interpretation":"Synthetic/unqualified odds and already-seen outcomes cannot establish a profitable strategy, even when a bootstrap lower bound is positive.",
    }
