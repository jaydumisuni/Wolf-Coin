from pathlib import Path
import json
from copy import deepcopy
import pytest
from wolf_lab.forward_market import QuoteRefused, digest, canonical
from wolf_lab.forward_evidence_reconcile import reconcile
from wolf_lab.forward_market_cli import ingest, verify
from hashlib import sha256

ROOT=Path("/home/kratos/projects/Wolf-Coin/.workspace/proof-history")
MLP=ROOT/"prelive-outcome-feedback-20261126/forward-freeze/forward-freeze-20261126.json"
GOAL=ROOT/"goal-poisson-20261126/goal-poisson-future-270.json"
SOURCE=ROOT/"forward-score-readiness-20261126/source-check.json"
PAIRED=ROOT/"forward-score-readiness-20261126/paired-readiness.json"
MARKET=ROOT/"forward-market-evidence-20261126/verified"

@pytest.fixture
def inputs():
    if not all(p.exists() for p in (MLP,GOAL,SOURCE,PAIRED,MARKET)):
        pytest.skip("owner-private evidence not mounted")
    return [MLP,GOAL,SOURCE,PAIRED,MARKET]

def altered(path, target, field, modify):
    obj=json.loads(path.read_bytes())
    modify(obj)
    obj.pop(field)
    obj[field]=digest(obj)
    target.write_bytes(canonical(obj))
    return target

def test_real_evidence_reconciles_without_inventing_settlements(inputs):
    result=reconcile(*inputs)
    assert result["forecast_count"]==270
    assert result["paired_outcomes"]==0
    assert result["pending_outcomes"]==270
    assert result["fixtures_with_quote_evidence"]==1
    assert result["rescheduled_quote_fixtures"]==1
    assert result["same_original_date_quote_and_result_pairs"]==0
    assert result["http_date_attestations_checked"]==1
    assert not result["predictive_superiority_proven"]

def test_resealed_mismatched_reports_are_refused(inputs,tmp_path):
    inputs[3]=altered(PAIRED,tmp_path/"pair.json","sha256",
                      lambda x:x.update(results_source_sha256="0"*64))
    with pytest.raises(QuoteRefused,match="different forecast or result"):
        reconcile(*inputs)

def test_resealed_wrong_coverage_is_refused(inputs,tmp_path):
    inputs[3]=altered(PAIRED,tmp_path/"pair.json","sha256",
                      lambda x:x.update(pending_outcomes=269))
    with pytest.raises(QuoteRefused,match="coverage"):
        reconcile(*inputs)

def test_future_result_is_refused(inputs,tmp_path):
    item=json.loads(MLP.read_bytes())["records"][0]
    key=item["identity"]
    def source_change(x):
        x.update(scored_count=1,unscored_count=269,matches=[dict(identity=key,outcome="H",fixture_day=item["fixture_day"],forecast_probabilities_1x2=item["probabilities_1x2"],brier=0)])
    def pair_change(x):
        x.update(paired_outcomes=1,pending_outcomes=269,paired_records=[dict(identity=key,settled_outcome="H")])
    inputs[2]=altered(SOURCE,tmp_path/"source.json","result_digest_sha256",source_change)
    inputs[3]=altered(PAIRED,tmp_path/"pair.json","sha256",pair_change)
    with pytest.raises(QuoteRefused,match="contradicts frozen fixture"):
        reconcile(*inputs)

def test_old_journal_version_cannot_be_silently_rewritten(inputs,tmp_path):
    directory=tmp_path/"private";directory.mkdir(mode=0o700)
    fixture=json.loads(MLP.read_bytes())["records"][0]
    for n in (1,2):
        raw=canonical(dict(type="wolf.provider-quote-observation.v1",
            fixture_identity=fixture["identity"],quoted_fixture_day=fixture["fixture_day"],
            kickoff_utc=fixture["fixture_day"]+"T15:00:00Z",observed_utc="2026-11-26T13:40:00Z",
            provider="Synthetic Test Quote",source_url="https://example.org/test",
            decimal_odds_1x2=[2.1,3.4,3.6],financial_execution_authorized=False,synthetic_fixture=True))
        quote=json.loads(raw)
        quote.pop("type");quote.pop("financial_execution_authorized");quote.pop("synthetic_fixture")
        quote.update(capture_id=f"capture:synthetic-{n}",evidence_sha256=sha256(raw).hexdigest())
        q=tmp_path/"quote.json";q.write_bytes(canonical(quote))
        s=tmp_path/"raw.json";s.write_bytes(raw)
        ingest(MLP,directory,q,s)
    assert verify(MLP,directory)["quotes_recorded"]==2
    first=directory/"journal-000001.json"
    obj=json.loads(first.read_bytes())
    obj["last_sha256"]="0"*64
    obj.pop("seal_sha256");obj["seal_sha256"]=digest(obj)
    first.write_bytes(canonical(obj))
    with pytest.raises(QuoteRefused,match="history differs"):
        verify(MLP,directory)

def test_resealed_attestation_with_foreign_tail_refused(inputs,tmp_path):
    import shutil
    directory=tmp_path/"private";shutil.copytree(MARKET,directory)
    directory.chmod(0o700)
    att=next(directory.glob("attestation-*.json"))
    obj=json.loads(att.read_bytes())
    obj["journal_tail_sha256"]="f"*64
    obj.pop("seal_sha256");obj["seal_sha256"]=digest(obj)
    att.chmod(0o600);att.write_bytes(canonical(obj))
    with pytest.raises(QuoteRefused,match="journal tail"):
        verify(MLP,directory)


def test_later_synthetic_report_checks_arithmetic_and_reschedule(inputs,tmp_path,monkeypatch):
    from datetime import datetime,timezone
    import wolf_lab.forward_evidence_reconcile as audit
    class TestClock(datetime):
        @classmethod
        def now(cls,tz=None):
            return cls(2026,12,1,tzinfo=timezone.utc)
    monkeypatch.setattr(audit,"datetime",TestClock)
    m=json.loads(MLP.read_bytes())["records"][0]
    g=json.loads(GOAL.read_bytes())["records"][0]
    def brier(row):
        return sum((p-(i==0))**2 for i,p in enumerate(row["probabilities_1x2"]))
    a,b=brier(m),brier(g)
    def source_change(x):
        x.update(capture_utc="2026-11-30T12:00:00Z",scored_count=1,unscored_count=269,
            matches=[dict(identity=m["identity"],outcome="H",fixture_day=m["fixture_day"],
                          forecast_probabilities_1x2=m["probabilities_1x2"],brier=round(a,12))])
    def pair_change(x):
        x.update(capture_utc="2026-11-30T12:00:00Z",paired_outcomes=1,pending_outcomes=269,
            paired_records=[dict(identity=m["identity"],settled_outcome="H",
                 original_mlp_brier=round(a,12),frozen_goal_poisson_brier=round(b,12),
                 mlp_minus_goal_brier=round(a-b,12))])
    inputs[2]=altered(SOURCE,tmp_path/"source.json","result_digest_sha256",source_change)
    inputs[3]=altered(PAIRED,tmp_path/"pair.json","sha256",pair_change)
    report=reconcile(*inputs)
    assert report["paired_outcomes"]==1
    assert report["same_original_date_quote_and_result_pairs"]==0
    assert report["rescheduled_quote_and_result_pairs_requiring_review"]==1
    assert not report["predictive_superiority_proven"]
    inputs[3]=altered(inputs[3],tmp_path/"bad.json","sha256",
                      lambda x:x["paired_records"][0].update(original_mlp_brier=100))
    with pytest.raises(QuoteRefused,match="arithmetic mismatch"):
        reconcile(*inputs)
