"""Independent standard-library verification of private loss-feedback journals.

This verifier never imports model training or reads third-party market data.
It independently recomputes the recorded adaptive proper scores and settled
loss counts from precommitted forecasts and source-matched outcome receipts.
Hashes bind local artifacts but do not authenticate real-world account data.
"""
from __future__ import annotations

from hashlib import sha256
from math import log
from pathlib import Path
import argparse
import json

from wolf_lab.loss_feedback import FeedbackError, LossLearner, _digest
from wolf_lab.prelive_qualification import SCHEMA, EVALUATE, MARKET_HASH


def _read_json(path:Path):
    data=path.read_bytes()
    if len(data)>12_000_000:
        raise FeedbackError("evidence file too large")
    try:
        return json.loads(data),sha256(data).hexdigest()
    except (UnicodeError,ValueError) as exc:
        raise FeedbackError("malformed evidence JSON") from exc


def verify(folder:Path)->dict:
    folder=folder.resolve()
    if not folder.is_dir():
        raise FeedbackError("qualification evidence directory absent")
    report,report_hash=_read_json(folder/"qualification.json")
    if not isinstance(report,dict) or report.get("schema")!=SCHEMA:
        raise FeedbackError("unexpected qualification report schema")
    sealed=dict(report)
    internal_hash=sealed.pop("seal_sha256",None)
    if internal_hash!=_digest(sealed):
        raise FeedbackError("qualification report seal mismatch")
    if report.get("mode")!="HISTORICAL_OFFLINE_ONLY" or report.get("no_funds_or_provider_connections") is not True or report.get("real_money_profit_proven") is not False or report.get("no_strategy_release_authority") is not True:
        raise FeedbackError("unsafe or mislabeled qualification result")
    entries=report.get("private_journals")
    folds=report.get("seasons")
    if not isinstance(entries,list) or not isinstance(folds,list) or len(entries)!=4 or len(folds)!=4:
        raise FeedbackError("four historical folds and journals required")
    if [x.get("season") for x in folds]!=list(EVALUATE) or [x.get("season") for x in entries]!=list(EVALUATE):
        raise FeedbackError("unexpected season sequence")
    settled=0;losses=0;win=0
    for index,season in enumerate(EVALUATE):
        meta=entries[index]
        expected_name="journal-"+season+".json"
        if meta.get("file")!=expected_name:
            raise FeedbackError("journal filename mismatch")
        state,file_hash=_read_json(folder/expected_name)
        if file_hash!=meta.get("file_sha256"):
            raise FeedbackError("journal artifact SHA-256 mismatch")
        replay=LossLearner.from_snapshot(state)
        if replay.snapshot()!=state:
            raise FeedbackError("journal restart state changed")
        fold=folds[index]
        if state.get("seal_sha256")!=fold.get("sealed_journal_sha256"):
            raise FeedbackError("fold journal seal mismatch")
        if replay.version!=fold.get("forecast_settlements") or len(replay.forecasts)!=fold.get("fixtures"):
            raise FeedbackError("forecast/settlement count mismatch")
        if len(replay.receipts)!=len(replay.forecasts):
            raise FeedbackError("incomplete learning outcomes")
        sum_brier=0.0;sum_log=0.0;fold_loss=0
        for pred_id,forecast in replay.forecasts.items():
            record=replay.receipts.get(pred_id)
            if not record:
                raise FeedbackError("missing outcome for forecast")
            actual=record["settlement"]["outcome_label"]
            y=[1.0 if i==actual else 0.0 for i in range(3)]
            probs=forecast.probabilities
            sum_brier+=sum((p-t)**2 for p,t in zip(probs,y))
            sum_log+=-log(probs[actual])
            if record["receipt"]["virtual_pnl"] < 0:
                fold_loss+=1
        count=len(replay.forecasts)
        score={"brier":round(sum_brier/count,9),"log_loss":round(sum_log/count,9)}
        if score!=fold["adaptive"] or fold_loss!=fold["synthetic_losing_receipts"]:
            raise FeedbackError("recomputed proper scores or loss count disagree")
        if fold.get("synthetic_winning_receipts")!=count-fold_loss:
            raise FeedbackError("invalid winning receipt total")
        if season in MARKET_HASH:
            market=fold.get("market_source")
            if not isinstance(market,dict) or market.get("source_sha256")!=MARKET_HASH[season] or market.get("matched_fixtures")!=380:
                raise FeedbackError("market comparison manifest mismatch")
        elif fold.get("market") is not None:
            raise FeedbackError("market comparison outside permitted seasons")
        settled+=count;losses+=fold_loss;win+=count-fold_loss
    if settled!=report.get("total_settled_learning_events") or losses!=report.get("settled_synthetic_losses"):
        raise FeedbackError("report aggregate settlements mismatch")
    if report.get("repeated_predictive_superiority_gate_passed") is not (
       report.get("historical_consistent_market_advantage") is True
       and report.get("historical_consistent_frozen_model_advantage") is True
    ):
        raise FeedbackError("reported gate inconsistent with inputs")
    if report.get("predictive_superiority_independently_proven") is not False or report.get("independent_future_unseen_holdout_evaluated") is not False:
        raise FeedbackError("not an independent future holdout")
    return {
        "schema":"wolf.loss-feedback-independent-journal-verifier.v1",
        "status":"MECHANISM_VERIFIED" if losses>0 else "NO_LOSS_SETTLEMENTS",
        "report_sha256":report_hash,
        "folds_checked":len(folds),
        "settled_forecasts_checked":settled,
        "losing_settlements_checked":losses,
        "winning_settlements_checked":win,
        "market_comparison_only_not_training":True,
        "statistical_market_superiority":report["historical_consistent_market_advantage"],
        "adaptive_promotion":"REJECT_KEEP_FROZEN" if not report["repeated_predictive_superiority_gate_passed"] else "AWAIT_NEW_UNTOUCHED_HOLDOUT",
        "authenticates_real_provider_settlement":False,
        "live_money_authorized":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(prog="wolf-prelive-verify")
    parser.add_argument("--evidence-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(verify(args.evidence_dir),sort_keys=True))
    except (FeedbackError,OSError,KeyError,ValueError,TypeError) as exc:
        parser.exit(2,"INDEPENDENT_VERIFICATION_FAILED: "+str(exc)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
