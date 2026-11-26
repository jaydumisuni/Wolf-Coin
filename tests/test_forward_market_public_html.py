"""Public pre-match website source, schedule and HTTP-header proof.

This is a dated public aggregator listing, NOT a quote authenticated by
the bookmaker itself and NOT an executable betting offer.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import json

import pytest

from wolf_lab.forward_market import MarketQuote,QuoteBook,QuoteRefused,canonical,frozen
from wolf_lab.forward_market_cli import ingest,verify,attest

ROOT=Path("/home/kratos/projects/Wolf-Coin/.workspace")
SOURCE=ROOT/"proof-history/prelive-outcome-feedback-20261126/forward-freeze/forward-freeze-20261126.json"
PUBLIC=ROOT/"proof-history/forward-market-evidence-20261126"


def source_files():
    html=PUBLIC/"tipsterarea-page.html"
    headers=PUBLIC/"tipsterarea-headers.txt"
    if not all(f.is_file() for f in (SOURCE,html,headers)):
        pytest.skip("private public-source retrieval not mounted")
    return html,headers


def typed():
    html,headers=source_files()
    raw=html.read_bytes()
    return MarketQuote(
        capture_id="capture:source-bound-arsenal-city-test",
        fixture_identity="2026-11-28|arsenal|manchester city",
        quoted_fixture_day="2026-11-29",
        kickoff_utc="2026-11-29T16:30:00Z",
        observed_utc="2026-11-26T13:48:17Z",
        provider="TipsterArea betfair",
        source_url="https://tipsterarea.com/match/arsenal-manchester-city-premier-league-england-957595",
        decimal_odds_1x2=(1.95,3.70,3.60),
        evidence_sha256=sha256(raw).hexdigest(),
        evidence_kind="public_1x2_html",
        schedule_source_url="https://tipsterarea.com/match/arsenal-manchester-city-premier-league-england-957595",
        schedule_evidence_sha256=sha256(raw).hexdigest()
    )


def test_actual_public_quote_exact_prices_and_schedule():
    html,_=source_files()
    book=QuoteBook(frozen(SOURCE))
    result=book.record(typed(),html.read_bytes(),schedule_raw=html.read_bytes())
    assert result["schedule_changed"] is True
    assert result["frozen_fixture_day"]=="2026-11-28"
    assert abs(sum(result["market_de_vig_1x2"])-1.0)<1e-10
    assert result["financial_action_authorized"] is False
    assert not result["independent_provider_authentication"]


def test_actual_public_html_wrong_price_and_changed_day_refused():
    html,_=source_files()
    raw=html.read_bytes()
    q=typed()
    book=QuoteBook(frozen(SOURCE))
    from dataclasses import replace
    with pytest.raises(QuoteRefused,match="captured prices disagree"):
        book.record(replace(q,decimal_odds_1x2=(2.2,3.7,3.6)),raw,schedule_raw=raw)
    with pytest.raises(QuoteRefused,match="page kickoff"):
        book.record(replace(q,kickoff_utc="2026-11-29T15:30:00Z"),raw,schedule_raw=raw)


def test_source_http_header_date_attached_without_mutating_quote(tmp_path):
    html,headers=source_files()
    folder=tmp_path/"private";folder.mkdir(mode=0o700)
    quote=typed()
    meta=tmp_path/"quote.json"
    meta.write_bytes(canonical(quote.__dict__))
    first=ingest(SOURCE,folder,meta,html,html)
    assert first["quotes_recorded"]==1
    assert verify(SOURCE,folder)["http_server_date_attestations_checked"]==0
    result=attest(SOURCE,folder,quote.capture_id,headers)
    assert result["status"]=="LOCAL_HTTP_DATE_PROOF_RECORDED"
    assert attest(SOURCE,folder,quote.capture_id,headers)==result
    assert verify(SOURCE,folder)["http_server_date_attestations_checked"]==1
    saved=next(folder.glob("attestation-*.json"))
    tampered=json.loads(saved.read_text())
    tampered["source_observed_utc"]="2026-11-26T12:48:17Z"
    saved.write_bytes(canonical(tampered))
    with pytest.raises(QuoteRefused,match="transport attestation seal"):
        verify(SOURCE,folder)


def test_public_date_header_mismatch_rejected(tmp_path):
    html,headers=source_files()
    from dataclasses import replace
    from wolf_lab.forward_market import _transport_proof
    item=typed()
    quote=replace(item,transport_evidence_sha256=sha256(headers.read_bytes()).hexdigest(),
                  observed_utc="2026-11-26T12:48:17Z")
    with pytest.raises(QuoteRefused,match="observed timestamp contradicts"):
        _transport_proof(headers.read_bytes(),quote)
