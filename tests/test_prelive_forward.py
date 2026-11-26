"""Prospective freeze integrity and future settlement isolation tests."""
from copy import deepcopy
from datetime import date
import pytest

from wolf_lab import prelive_forward as future
from wolf_lab.typed_tabular import TypedRouteRefused


def fabricated():
    records=[]
    for n in range(60):
        day=f"2027-01-{(n//3)+1:02d}"
        records.append({
            "identity":f"{day}|Club{n}|Other{n}",
            "fixture_day":day,
            "prior_only_features":[1.0,0.0],
            "probabilities_1x2":[0.45,0.25,0.30],
            "result_known_at_freeze":False,
        })
    v={
        "schema":future.SCHEMA,"status":"FROZEN_PENDING_UNSEEN_FUTURE_OUTCOMES",
        "cutoff_date":future.AS_OF.isoformat(),
        "frozen_model_sha256":future.MODEL_FROZEN_FILE_SHA256,
        "fixture_snapshot_sha256":future.EXPECTED_FINAL_SOURCE_SHA256,
        "authority":future.RESEARCH_ONLY,
        "live_admission":False,"financial_edge_proven":False,
        "market_odds_available":False,
        "future_match_count":len(records),"records":records,
    }
    v["forecast_digest_sha256"]=future._sha(v)
    return v


def test_forward_freeze_is_source_bound_and_has_no_early_outcomes():
    v=fabricated()
    assert future.verify_freeze(v)
    corrupted=deepcopy(v)
    corrupted["records"][0]["probabilities_1x2"][0]=0.99
    with pytest.raises(TypedRouteRefused,match="digest"):
        future.verify_freeze(corrupted)
    corrupted=deepcopy(v)
    corrupted["live_admission"]=True
    with pytest.raises(TypedRouteRefused,match="contract"):
        future.verify_freeze(corrupted)


def test_future_scoring_requires_later_exact_receipts():
    v=fabricated()
    row=v["records"][0]
    outcome={"schema":"wolf.prelive-future-outcomes.v1",
             "observed_day":"2027-01-24",
             "outcomes":[{"identity":row["identity"],"outcome":"H",
                          "settled_day":"2027-01-03"}]}
    scored=future.score_future_after_settlement(
        v,outcome,independent_results_source_sha256="c"*64)
    assert scored["outcomes_scored"]==1 and scored["remaining_frozen_predictions"]==59
    assert scored["live_admission"] is False
    assert scored["market_baseline_pending"] is True
    assert abs(scored["forecast_brier"]-(0.55**2+0.25**2+0.3**2))<1e-9
    for edit in ("unknown","duplicate","early","future","malformed","past_observation"):
        invalid=deepcopy(outcome)
        if edit=="unknown":invalid["outcomes"][0]["identity"]="2027-01-01|Missing|Wrong"
        elif edit=="duplicate":invalid["outcomes"].append(invalid["outcomes"][0])
        elif edit=="early":invalid["outcomes"][0]["settled_day"]="2027-01-01"
        elif edit=="future":invalid["outcomes"][0]["settled_day"]="2027-01-25"
        elif edit=="malformed":invalid["outcomes"][0]["outcome"]="WIN"
        else:invalid["observed_day"]="2026-11-26"
        with pytest.raises(TypedRouteRefused):
            future.score_future_after_settlement(
                v,invalid,independent_results_source_sha256="c"*64)
