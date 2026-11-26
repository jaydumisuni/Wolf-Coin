"""End-to-end immutable forward market quote CLI evidence tests."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import pytest

from wolf_lab.forward_market import frozen,canonical,QuoteRefused
from wolf_lab.forward_market_cli import ingest,verify,probe

SOURCE=Path("/home/kratos/projects/Wolf-Coin/.workspace/proof-history/prelive-outcome-feedback-20261126/forward-freeze/forward-freeze-20261126.json")


def test_capture_then_replay_preserves_frozen_universe(tmp_path):
    if not SOURCE.is_file():
        pytest.skip("private prospective freeze not mounted")
    f=frozen(SOURCE)["records"][0]
    directory=tmp_path/"private"
    directory.mkdir(mode=0o700)
    snapshot={
        "type":"wolf.provider-quote-observation.v1",
        "fixture_identity":f["identity"],
        "quoted_fixture_day":f["fixture_day"],
        "kickoff_utc":f["fixture_day"]+"T15:00:00Z",
        "observed_utc":"2026-11-26T13:40:00Z",
        "provider":"Synthetic Test Quote",
        "source_url":"https://example.org/fixture-test",
        "decimal_odds_1x2":[2.25,3.5,3.8],
        "financial_execution_authorized":False,
        "synthetic_fixture":True
    }
    raw=canonical(snapshot)
    quote={key:snapshot[key] for key in (
        "fixture_identity","quoted_fixture_day","kickoff_utc","observed_utc",
        "provider","source_url","decimal_odds_1x2")}
    quote.update(capture_id="capture:syn-quote-0001",
                 evidence_sha256=sha256(raw).hexdigest(),
                 evidence_kind="provider_snapshot_json",
                 schedule_source_url=None,schedule_evidence_sha256=None)
    quote_file=tmp_path/"quote.json";quote_file.write_bytes(canonical(quote))
    snapshot_file=tmp_path/"snapshot.json";snapshot_file.write_bytes(raw)
    one=ingest(SOURCE,directory,quote_file,snapshot_file)
    assert one["status"]=="PROVISIONAL_MARKET_CAPTURED"
    assert one["independent_price_authentication"] is False
    assert one["quotes_recorded"]==1
    assert verify(SOURCE,directory)["quotes_recorded"]==1
    assert ingest(SOURCE,directory,quote_file,snapshot_file)["status"]=="IDEMPOTENT_EXISTING_CAPTURE"
    assert len(list(directory.glob("journal-*.json")))==1
    data=json.loads((directory/"journal-000001.json").read_text())
    assert data["no_funding_authority"] and data["independent_authentication_incomplete"]
    data["records"][0]["record"]["market_overround"]=-1.5
    (directory/"journal-000001.json").write_bytes(canonical(data))
    with pytest.raises(QuoteRefused,match="journal seal mismatch"):
        verify(SOURCE,directory)


def test_malformed_html_csv_from_public_source_refused(tmp_path):
    html=b"<HTML><TITLE>Soccer betting odds fixtures page</TITLE></HTML>"
    file=tmp_path/"fixtures.csv"
    file.write_bytes(html)
    result=probe(file)
    assert result["status"]=="REJECT_HTML_NOT_MARKET_CSV"
    assert result["sha256"]==sha256(html).hexdigest()


def test_immutable_journal_numbering_gap_refused(tmp_path):
    if not SOURCE.is_file():
        pytest.skip("private prospective freeze not mounted")
    directory=tmp_path/"private";directory.mkdir(mode=0o700)
    (directory/"journal-000002.json").write_text("{}")
    with pytest.raises(QuoteRefused,match="numbering gap"):
        verify(SOURCE,directory)
