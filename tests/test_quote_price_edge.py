"""Offline 1X2 quote importer and loss-aware paper-shadow negative controls."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
import json

import pytest

from wolf_markets.quote_book import QuoteRefused,load_quote_book,quote_book_summary
from wolf_lab.price_edge import (
    EdgeRefused, candidates_before_results, score_shadow,
    synthetic_quote_template,MIN_VALIDATED_BETS
)


def forecasts(n=1):
    return [
        {"id":f"2026-08-{10+i:02}|team_{i}_home|team_{i}_away",
         "prior_day_features":[0.5]*10,
         "class_probabilities":[0.60,0.20,0.20]}
        for i in range(n)
    ]


def store(tmp_path,data):
    p=tmp_path/"quotes.json"
    p.write_text(json.dumps(data,sort_keys=True))
    return p,sha256(p.read_bytes()).hexdigest()


def load(tmp_path,data):
    p,d=store(tmp_path,data)
    return load_quote_book(p,expected_sha256=d)


def test_valid_simulated_quote_research_only(tmp_path):
    b=load(tmp_path,synthetic_quote_template(forecasts()))
    assert len(b.quotes)==3 and b.executable is False
    s=quote_book_summary(b)
    assert s["fixture_count"]==1
    assert not s["verified_provider_permission"]
    assert not s["verified_account_executable_odds"]
    assert not s["live_execution_allowed"]


def test_price_inference_and_paper_net_does_not_prove_profit(tmp_path):
    prediction=forecasts()
    b=load(tmp_path,synthetic_quote_template(prediction))
    selected=candidates_before_results(b,prediction)
    assert len(selected)==1 and selected[0].outcome=="H"
    a=score_shadow(b,prediction,{prediction[0]["id"]:"H"},independent_model_verified=True)
    assert a["selected_hypothetical_bets"]==1
    assert a["hypothetical_net_ZMW"]=="0.535000"
    assert not a["positive_ev_proven"]
    assert not a["financial_authority"]
    assert not a["real_money_profit_proven"]
    assert not a["sufficient_sample_for_real_money_claim"]


def test_outcomes_do_not_change_preselection(tmp_path):
    prediction=forecasts(2)
    b=load(tmp_path,synthetic_quote_template(prediction))
    before=candidates_before_results(b,prediction)
    wins={p["id"]:"H" for p in prediction}
    losses={p["id"]:"A" for p in prediction}
    a=score_shadow(b,prediction,wins,independent_model_verified=True)
    z=score_shadow(b,prediction,losses,independent_model_verified=True)
    assert before==candidates_before_results(b,prediction)
    assert a["hypothetical_net_ZMW"]!=z["hypothetical_net_ZMW"]
    assert a["selected_hypothetical_bets"]==z["selected_hypothetical_bets"]


def test_abstain_when_no_validated_estimated_margin(tmp_path):
    rows=forecasts()
    rows[0]["class_probabilities"]=[0.33,0.33,0.34]
    fixture=synthetic_quote_template(rows)
    for quote,odd in zip(fixture["quotes"],("2.00","3.00","3.00")):
        quote["decimal_odds"]=odd
    b=load(tmp_path,fixture)
    x=score_shadow(b,rows,{rows[0]["id"]:"H"},independent_model_verified=True)
    assert x["selected_hypothetical_bets"]==0
    assert x["hypothetical_net_ZMW"]=="0.000000"


def test_source_digest_wrong_fails_closed(tmp_path):
    p,_=store(tmp_path,synthetic_quote_template(forecasts()))
    with pytest.raises(QuoteRefused,match="pinned SHA"):
        load_quote_book(p,expected_sha256="0"*64)


@pytest.mark.parametrize("field,value,reason",[
    ("source_kind","PROVIDER_LIVE","offline/unqualified"),
    ("capture_rights","LICENSED_LIVE","self-certify"),
    ("account_executable",True,"executable-account"),
    ("provider_account_verified",True,"executable-account"),
    ("currency","USD","currency bridge"),
])
def test_local_claims_never_create_live_venue(tmp_path,field,value,reason):
    x=synthetic_quote_template(forecasts())
    x[field]=value
    with pytest.raises(QuoteRefused,match=reason):
        load(tmp_path,x)


def test_reject_quote_after_kickoff(tmp_path):
    x=synthetic_quote_template(forecasts())
    x["quotes"][0]["offered_at"]=x["quotes"][0]["starts_at"]
    with pytest.raises(QuoteRefused,match="after kickoff"):
        load(tmp_path,x)


def test_reject_inconsistent_quotes_in_same_fixture(tmp_path):
    x=synthetic_quote_template(forecasts())
    x["quotes"][1]["offered_at"]="2026-08-07T15:00:00+00:00"
    with pytest.raises(QuoteRefused,match="incompatible"):
        load(tmp_path,x)


def test_reject_naive_timestamp_or_timezone(tmp_path):
    x=synthetic_quote_template(forecasts())
    x["quotes"][0]["starts_at"]="2026-08-10T15:00:00"
    with pytest.raises(QuoteRefused,match="UTC"):
        load(tmp_path,x)
    x["quotes"][0]["starts_at"]="2026-08-10T15:00:00+02:00"
    with pytest.raises(QuoteRefused,match="UTC"):
        load(tmp_path,x)


def test_reject_incomplete_quote_set(tmp_path):
    x=synthetic_quote_template(forecasts())
    x["quotes"].pop()
    with pytest.raises(QuoteRefused,match="count|incomplete"):
        load(tmp_path,x)


def test_reject_duplicated_json_keys_even_if_hash_matches(tmp_path):
    raw=b'{"schema":"wolf.research-quotes.v1","schema":"LIVE"}'
    p=tmp_path/"bad.json"
    p.write_bytes(raw)
    with pytest.raises(QuoteRefused,match="duplicate"):
        load_quote_book(p,expected_sha256=sha256(raw).hexdigest())


def test_reject_oversized_or_nan_odds(tmp_path):
    x=synthetic_quote_template(forecasts())
    x["quotes"][0]["decimal_odds"]="NaN"
    with pytest.raises(QuoteRefused,match="canonical"):
        load(tmp_path,x)
    x["quotes"][0]["decimal_odds"]="10000.0"
    with pytest.raises(QuoteRefused,match="outside bounded"):
        load(tmp_path,x)


def test_reject_unqualified_results_or_model(tmp_path):
    rows=forecasts()
    b=load(tmp_path,synthetic_quote_template(rows))
    with pytest.raises(EdgeRefused,match="verification"):
        score_shadow(b,rows,{rows[0]["id"]:"H"},independent_model_verified=False)
    with pytest.raises(EdgeRefused,match="exactly bound"):
        score_shadow(b,rows,{"foreign":"H"},independent_model_verified=True)


def test_duplicate_forecast_id_and_missing_quote_refuse(tmp_path):
    rows=forecasts()
    b=load(tmp_path,synthetic_quote_template(rows))
    with pytest.raises(EdgeRefused,match="duplicate"):
        candidates_before_results(b,rows+rows)
    other=forecasts()
    other[0]["id"]="2026-08-12|different|teams"
    with pytest.raises(EdgeRefused,match="missing complete quote"):
        candidates_before_results(b,other)


def test_cannot_self_qualify_with_200_synthetic_bets(tmp_path):
    rows=forecasts(11)
    b=load(tmp_path,synthetic_quote_template(rows))
    out={r["id"]:"H" for r in rows}
    a=score_shadow(b,rows,out,independent_model_verified=True)
    assert a["quoted_fixture_count"]==11
    assert a["qualified_bet_count_threshold"]==MIN_VALIDATED_BETS
    assert not a["real_money_profit_proven"]
    assert not a["live_provider_api_verified"]
