"""Regression and negative controls for source-separated uncertainty audit."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from wolf_lab.uncertainty import audit_shadow_uncertainty, SCHEMA,SEED,REPETITIONS
from wolf_lab.price_edge import EdgeRefused,synthetic_quote_template
from wolf_lab.typed_tabular import prior_only_rows
from wolf_markets.quote_book import load_quote_book


@pytest.fixture(scope="module")
def real_case():
    root=Path('/home/kratos/projects/Wolf-Coin/.workspace')
    frozen=root/'proof-history/tabular-20261123/typed-candidate.json'
    odds=root/'proof-history/five-gates-20261123/explicitly-synthetic-1x2-quotes.json'
    data=root/'research/external/openfootball-cc0-20261123'
    if not all(x.exists() for x in (frozen,odds,data)):
        pytest.skip("private KRATOS evidence unavailable")
    rows=json.loads(frozen.read_text())['predictions']
    observed={'|'.join(x.key):('H','D','A')[x.label] for x in prior_only_rows(data)}
    source=load_quote_book(odds,expected_sha256=sha256(odds.read_bytes()).hexdigest())
    return source,rows,observed


def test_bootstrap_is_reproducible_source_bound_and_uncertain(real_case):
    quote,rows,outcomes=real_case
    result=audit_shadow_uncertainty(quote,rows,outcomes,independent_model_verified=True)
    assert result==audit_shadow_uncertainty(quote,rows,outcomes,independent_model_verified=True)
    assert result['schema']==SCHEMA
    assert result['fixed_bootstrap_seed']==SEED
    assert result['clustered_bootstrap_repetitions']==REPETITIONS
    assert result['distinct_match_days']==17
    assert result['selected_hypothetical_bets']==36
    assert result['hypothetical_total_net_ZMW']=='5.610000'
    assert result['clustered_bootstrap_lower_95pct_ZMW']=='-2.565500'
    assert result['clustered_bootstrap_upper_95pct_ZMW']=='13.620500'
    assert result['interval_includes_zero'] is True
    assert result['profitability_proven'] is False
    assert result['venue_approval'] is False


def test_cannot_relabel_synthetic_gain_as_money(real_case):
    quote,rows,outcomes=real_case
    p=audit_shadow_uncertainty(quote,rows,outcomes,independent_model_verified=True)
    assert p['source_kind']=='SIMULATED_ONLY'
    assert p['quote_source_executable'] is False
    assert p['market_data_rights_verified'] is False
    assert p['external_investment_or_betting_recommendation'] is False
    assert p['previously_seen_2026_27_results'] is True


def test_unverified_model_prevents_score_proof(real_case):
    quote,rows,outcomes=real_case
    with pytest.raises(EdgeRefused,match='verification'):
        audit_shadow_uncertainty(quote,rows,outcomes,independent_model_verified=False)


def test_corrupt_outcomes_not_accepted(real_case):
    quote,rows,outcomes=real_case
    changed=dict(outcomes)
    changed.pop(next(iter(changed)))
    with pytest.raises(EdgeRefused,match='exactly bound'):
        audit_shadow_uncertainty(quote,rows,changed,independent_model_verified=True)


def test_small_n_is_rejected_not_scaled_to_claim_large_evidence(tmp_path):
    rows=[
        {'id':f'2026-08-{i+1:02}|home{i}|away{i}',
         'prior_day_features':[0.5]*10,
         'class_probabilities':[0.60,0.20,0.20]}
         for i in range(4)
    ]
    doc=synthetic_quote_template(rows)
    p=tmp_path/'synthetic.json'
    p.write_text(json.dumps(doc,sort_keys=True))
    book=load_quote_book(p,expected_sha256=sha256(p.read_bytes()).hexdigest())
    outcomes={r['id']:'H' for r in rows}
    with pytest.raises(EdgeRefused,match='too little independent history'):
        audit_shadow_uncertainty(book,rows,outcomes,independent_model_verified=True)


def test_different_outcomes_change_uncertainty_not_selection(real_case):
    book,rows,outcomes=real_case
    x=audit_shadow_uncertainty(book,rows,outcomes,independent_model_verified=True)
    altered={k:'A' for k in outcomes}
    y=audit_shadow_uncertainty(book,rows,altered,independent_model_verified=True)
    assert x['selected_hypothetical_bets']==y['selected_hypothetical_bets']
    assert x['hypothetical_total_net_ZMW']!=y['hypothetical_total_net_ZMW']
    assert y['profitability_proven'] is False
