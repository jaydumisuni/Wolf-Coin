"""Controlled application settlement-to-learning qualification.

The existing application's transaction contract does not include a sports
result or a prediction reference. This adapter checks an explicit evidence
binding in a controlled fixture, then updates a separate offline learner.
It does not authenticate provider outcomes or modify an application database.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from wolf_app.store import ApplicationStore
from wolf_lab.loss_feedback import Forecast, Settlement, LossLearner, FeedbackError

SCHEMA = "wolf.controlled-settlement-learning.v1"

def _stamp(s):
    value = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
        raise FeedbackError("UTC evidence required")
    return value

def replay(db_path: Path, learner: LossLearner, raw: bytes):
    """Return a new learner and a local evidence receipt; never mutate input.

    The caller must preserve the prior frozen forecast journal. Controlled
    fixture payloads are NOT eligible as genuine provider settlements.
    """
    evidence = json.loads(raw)
    expected = {"schema", "controlled_fixture", "account_id", "decision_id",
                "transaction_id", "observation_id", "match_id", "outcome_label",
                "settled_utc", "stake", "decimal_odds"}
    if (not isinstance(evidence, dict) or set(evidence) != expected
        or evidence["schema"] != SCHEMA or evidence["controlled_fixture"] is not True):
        raise FeedbackError("explicit controlled evidence contract required")
    if not isinstance(learner, LossLearner):
        raise FeedbackError("offline learner required")
    cloned = LossLearner.from_snapshot(learner.snapshot())
    aid, pid, txid, oid = (evidence[k] for k in
                           ("account_id", "decision_id", "transaction_id", "observation_id"))
    forecast = cloned.forecasts.get(pid)
    if forecast is None or forecast.match_id != evidence["match_id"]:
        raise FeedbackError("no matching precommitted forecast")
    if not db_path.is_file() or db_path.is_symlink():
        raise FeedbackError("existing application database required")
    source_hash = sha256(raw).hexdigest()
    with closing(sqlite3.connect(db_path.resolve().as_uri()+"?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        audit_count = ApplicationStore.verify_audit_connection(db)
        scope = ("sports", aid)
        decision = db.execute("""SELECT instrument, action_kind, proposed_amount,
            status,result_ref,recorded_at FROM app_decisions
            WHERE domain=? AND account_id=? AND decision_id=?""", (*scope,pid)).fetchone()
        if (decision is None or decision[0] != forecast.match_id or decision[1] != "PLACE_BET"
            or decision[3] != "AWAITING_PLATFORM_RECONCILIATION" or decision[4] != txid):
            raise FeedbackError("missing matching native submission receipt")
        tx = db.execute("""SELECT kind,amount,status,occurred_at,source_observation_id
            FROM app_transactions WHERE domain=? AND account_id=? AND transaction_id=?""",
            (*scope,txid)).fetchone()
        if tx is None or tx[0] != "BET" or tx[2] != "SETTLED" or tx[4] != oid:
            raise FeedbackError("matching settled transaction readback required")
        obs = db.execute("""SELECT observed_at, evidence_sha256 FROM app_observations
            WHERE domain=? AND account_id=? AND observation_id=?""",(*scope,oid)).fetchone()
        if obs is None or obs[1] != source_hash:
            raise FeedbackError("settlement evidence bytes do not match observation")
        if Decimal(decision[2]) != Decimal(tx[1]) or Decimal(str(evidence["stake"])) != Decimal(tx[1]):
            raise FeedbackError("stake differs from the precommitted decision or transaction")
        if not (_stamp(forecast.forecast_utc) <= _stamp(decision[5])
                <= _stamp(tx[3]) <= _stamp(evidence["settled_utc"]) <= _stamp(obs[0])
                <= datetime.now(timezone.utc)):
            raise FeedbackError("settlement chronology does not reconcile")
        # Receipt and readback must occur in this order in the audited application.
        receipts, observations = [], []
        for seq,kind,body in db.execute("SELECT seq,event_kind,event_json FROM app_audit ORDER BY seq"):
            event = json.loads(body)
            if event.get("domain") != "sports" or event.get("account_id") != aid:
                continue
            if (kind == "decision.receipt" and event.get("decision_id") == pid
                and event.get("result_ref") == txid
                and event.get("outcome") == "NATIVE_REPORTED_SUBMITTED"):
                receipts.append(seq)
            if kind == "observation.ingest" and event.get("observation_id") == oid:
                observations.append(seq)
        if len(receipts) != 1 or len(observations) != 1 or receipts[0] >= observations[0]:
            raise FeedbackError("native receipt/readback audit ordering not proven")
    settlement = Settlement("settle:"+sha256((aid+"|"+txid).encode()).hexdigest(),
                            pid,evidence["settled_utc"],evidence["outcome_label"],
                            forecast.source_sha256,evidence["stake"],evidence["decimal_odds"])
    receipt = cloned.settle(settlement)
    return cloned, {"schema":SCHEMA,"controlled_fixture":True,
                    "account_id":aid,"decision_id":pid,"transaction_id":txid,
                    "evidence_sha256":source_hash,"application_audit_count":audit_count,
                    "learning_receipt":receipt,
                    "learning_journal_seal":cloned.snapshot()["seal_sha256"],
                    "provider_authentication_proven":False,
                    "real_money_profit_proven":False}
