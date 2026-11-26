"""Pre-match quote intake is deliberately separate from actual account/order APIs."""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from pathlib import Path
from copy import deepcopy
import json

import pytest

from wolf_lab.forward_market import (
    MarketQuote,QuoteBook,QuoteRefused,canonical,digest,frozen,immutable
)

FREEZE=Path("/home/kratos/projects/Wolf-Coin/.workspace/proof-history/prelive-outcome-feedback-20261126/forward-freeze/forward-freeze-20261126.json")


def source():
    if not FREEZE.is_file():
        pytest.skip("owner-private frozen prospective source not mounted")
    return frozen(FREEZE)


def observation(fixture,*,cid="capture:syn-test-0001",when="2026-11-26T13:40:00Z",
                day=None,kickoff=None,price=(2.10,3.40,3.60)):
    day=day or fixture["fixture_day"]
    kickoff=kickoff or day+"T15:00:00Z"
    values=dict(
        capture_id=cid,fixture_identity=fixture["identity"],quoted_fixture_day=day,
        kickoff_utc=kickoff,observed_utc=when,provider="Synthetic Test Quote",
        source_url="https://example.org/fixture-test-synthetic",
        decimal_odds_1x2=price,evidence_kind="provider_snapshot_json",
        evidence_sha256="0"*64
    )
    raw=canonical(dict(
        type="wolf.provider-quote-observation.v1",provider=values["provider"],
        source_url=values["source_url"],fixture_identity=values["fixture_identity"],
        quoted_fixture_day=day,kickoff_utc=kickoff,observed_utc=when,
        decimal_odds_1x2=price,financial_execution_authorized=False,
        synthetic_fixture=True))
    values["evidence_sha256"]=sha256(raw).hexdigest()
    return MarketQuote(**values),raw


def test_freeze_source_integrity_and_future_fixture_universe(tmp_path):
    x=source()
    assert x["future_match_count"]==270
    changed=tmp_path/"fake.json"
    data=FREEZE.read_bytes()
    changed.write_bytes(data[:-2]+b"  ")
    with pytest.raises(QuoteRefused,match="original prospective forecast bytes changed"):
        frozen(changed)


def test_quote_records_de_vig_without_orders_or_authority(tmp_path):
    x=source()
    b=QuoteBook(x)
    q,raw=observation(x["records"][0])
    result=b.record(q,raw)
    assert result["financial_action_authorized"] is False
    assert result["independent_provider_authentication"] is False
    assert result["price_executable_at_provider"] is False
    assert abs(sum(result["market_de_vig_1x2"])-1)<1e-10
    assert result["market_overround"]>0
    assert result["schedule_changed"] is False
    assert b.record(q,raw)==result
    assert len(b.records)==1


def test_source_bytes_matched_not_just_claimed_values():
    x=source()
    b=QuoteBook(x)
    q,raw=observation(x["records"][0])
    with pytest.raises(QuoteRefused,match="SHA-256 mismatch"):
        b.record(q,raw+b"tampered")
    bad=replace(q,decimal_odds_1x2=(2.8,3.4,3.6))
    with pytest.raises(QuoteRefused,match="source quote does not match"):
        b.record(bad,raw)
    assert not b.records


def test_missing_or_html_weekly_csv_never_admitted():
    x=source()
    b=QuoteBook(x)
    q,raw=observation(x["records"][0])
    html=b"<HTML><HEAD><TITLE>Fixtures</TITLE></HEAD><BODY>Download CSV</BODY></HTML>"
    with pytest.raises(QuoteRefused,match="not structured evidence JSON"):
        b.record(replace(q,evidence_sha256=sha256(html).hexdigest()),html)
    with pytest.raises(QuoteRefused,match="source quote does not match"):
        b.record(replace(q,evidence_sha256=sha256(canonical({"message":"not quotes"})).hexdigest()),
                 canonical({"message":"not quotes"}))


def test_incorrect_kickoff_or_post_kickoff_quotes_refused():
    x=source()
    f=x["records"][0]
    with pytest.raises(QuoteRefused,match="post-kickoff"):
        observation(f,when="2026-11-29T18:00:00Z",kickoff="2026-11-28T15:00:00Z")
    with pytest.raises(QuoteRefused,match="quoted date and UTC kickoff disagree"):
        observation(f,day="2026-11-28",kickoff="2026-11-29T15:00:00Z")
    with pytest.raises(QuoteRefused,match="future-dated"):
        observation(f,when="2099-11-26T13:40:00Z",day="2100-01-01",kickoff="2100-01-01T15:00:00Z")


def test_duplicate_capture_and_out_of_universe_refused():
    x=source();b=QuoteBook(x)
    q,raw=observation(x["records"][0])
    b.record(q,raw)
    other,other_bytes=observation(x["records"][1],cid=q.capture_id)
    with pytest.raises(QuoteRefused,match="conflicting repeated"):
        b.record(other,other_bytes)
    alien=replace(q,capture_id="capture:alien",fixture_identity="2026-11-29|unlisted|unknown")
    with pytest.raises(QuoteRefused,match="outside original"):
        b.record(alien,raw)


def test_reschedule_explicit_evidence_required(tmp_path):
    x=source()
    f=next(e for e in x["records"] if e["identity"]=="2026-11-28|arsenal|manchester city")
    q,raw=observation(f,cid="capture:rescheduled",day="2026-11-29",
                      kickoff="2026-11-29T16:30:00Z")
    b=QuoteBook(x)
    with pytest.raises(QuoteRefused,match="independent schedule evidence"):
        b.record(q,raw)
    evidence=canonical(dict(type="wolf.public-schedule-evidence.v1",
            source_url="https://example.org/synthetic-schedule",
            fixture_identity=f["identity"],
            current_kickoff_utc="2026-11-29T16:30:00Z",
            note="synthetic scheduling fixture for unit test"))
    q=replace(q,schedule_source_url="https://example.org/synthetic-schedule",
              schedule_evidence_sha256=sha256(evidence).hexdigest())
    with pytest.raises(QuoteRefused,match="schedule evidence source SHA-256"):
        b.record(q,raw,schedule_raw=evidence+b"?")
    r=b.record(q,raw,schedule_raw=evidence)
    assert r["schedule_changed"]
    assert r["frozen_fixture_day"]=="2026-11-28"
    assert b.source["records"][0]["result_known_at_freeze"] is False


def test_sealed_quote_journal_replay_and_forged_provenance_rejected(tmp_path):
    x=source()
    b=QuoteBook(x)
    q,raw=observation(x["records"][0])
    b.record(q,raw)
    priv=tmp_path/"private"
    priv.mkdir(mode=0o700)
    checksum=immutable(priv/(q.evidence_sha256+".json"),raw)
    assert checksum==q.evidence_sha256
    state=b.snapshot()
    immutable(priv/"journal.json",canonical(state))
    same=QuoteBook.replay(x,json.loads((priv/"journal.json").read_text()),priv)
    assert same.snapshot()==state
    with pytest.raises(FileExistsError):
        immutable(priv/(q.evidence_sha256+".json"),raw)
    forged=deepcopy(state)
    forged["records"][0]["record"]["market_de_vig_1x2"][0]=0.99
    forged.pop("seal_sha256")
    forged["seal_sha256"]=digest(forged)
    with pytest.raises(QuoteRefused,match="quote event digest mismatch"):
        QuoteBook.replay(x,forged,priv)


def test_bad_prices_and_untrusted_source_urls_refused():
    x=source()
    q,raw=observation(x["records"][0])
    for p in ((1.0,2.0,2.0),(float("nan"),3.0,3.0),(-3.0,3.0,3.0)):
        with pytest.raises(QuoteRefused,match="prices"):
            replace(q,decimal_odds_1x2=p)
    with pytest.raises(QuoteRefused,match="HTTPS"):
        replace(q,source_url="http://example.org/path")
    with pytest.raises(QuoteRefused,match="public source"):
        replace(q,source_url="https://localhost/foo")


def test_impossible_market_margin_refused():
    x=source();b=QuoteBook(x)
    q,raw=observation(x["records"][0],price=(4.5,4.5,4.5))
    with pytest.raises(QuoteRefused,match="implausible"):
        b.record(q,raw)


def test_timestamp_restrictions_do_not_claim_external_authentication():
    x=source();q,raw=observation(x["records"][0])
    assert q.observed_utc.endswith("Z")
    b=QuoteBook(x);b.record(q,raw)
    snap=b.snapshot()
    assert snap["independent_authentication_incomplete"] is True
    assert snap["no_funding_authority"] is True
    assert "quote" in snap["records"][0]["record"]
