"""Offline loss-feedback learning, sealed settlement journal; no execution API.

The decision is emitted BEFORE the result is known. Both wins and losses
update a bounded three-class online calibrator. A receipt is required before
any update. This mechanism cannot move funds, log in, or place an order.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from math import exp, isfinite, log
from pathlib import Path
import json
import os
import re

SCHEMA = "wolf.loss-feedback-journal.v1"
LEARNING_RATE = 0.04
MAX_BIAS = 0.70
SHRINK = 0.001
ODDS_SOURCE = "SYNTHETIC_OFFLINE_EXERCISE_ONLY"


class FeedbackError(ValueError):
    pass


def _canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(obj: object) -> str:
    return sha256(_canonical(obj)).hexdigest()


def _datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise FeedbackError("UTC timestamp ending in Z required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise FeedbackError("invalid UTC timestamp") from exc
    if result.utcoffset().total_seconds() != 0:
        raise FeedbackError("non-UTC timestamp")
    return result


def _probs(p) -> tuple[float, float, float]:
    if not isinstance(p, (tuple, list)) or len(p) != 3:
        raise FeedbackError("three probabilities required")
    if any(type(x) not in (float, int) or not isfinite(x) or x <= 0 or x >= 1 for x in p):
        raise FeedbackError("invalid forecast probabilities")
    result = tuple(float(x) for x in p)
    if abs(sum(result)-1) > 1e-8:
        raise FeedbackError("forecast probabilities not normalized")
    return result


def _identity(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9:_|.\-]{4,220}", value):
        raise FeedbackError("invalid event identity")
    return value


def _sha256(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise FeedbackError("source SHA-256 required")
    return value


@dataclass(frozen=True)
class Forecast:
    prediction_id: str
    match_id: str
    forecast_utc: str
    probabilities: tuple[float, float, float]
    selected_label: int
    source_sha256: str
    learning_version: int = 0

    def __post_init__(self):
        if type(self.learning_version) is not int or self.learning_version < 0:
            raise FeedbackError("invalid forecast learning version")
        _identity(self.prediction_id)
        _identity(self.match_id)
        _datetime(self.forecast_utc)
        _probs(self.probabilities)
        if type(self.selected_label) is not int or self.selected_label not in (0,1,2):
            raise FeedbackError("invalid selected outcome")
        _sha256(self.source_sha256)


@dataclass(frozen=True)
class Settlement:
    settlement_id: str
    prediction_id: str
    settled_utc: str
    outcome_label: int
    source_sha256: str
    stake: float
    decimal_odds: float

    def __post_init__(self):
        _identity(self.settlement_id)
        _identity(self.prediction_id)
        _datetime(self.settled_utc)
        _sha256(self.source_sha256)
        if type(self.outcome_label) is not int or self.outcome_label not in (0,1,2):
            raise FeedbackError("invalid settlement outcome")
        if type(self.stake) not in (float,int) or not isfinite(self.stake) or not 0 < self.stake <= 100:
            raise FeedbackError("invalid bounded simulated stake")
        if type(self.decimal_odds) not in (float,int) or not isfinite(self.decimal_odds) or not 1 < self.decimal_odds <= 100:
            raise FeedbackError("invalid bounded synthetic odds")


class LossLearner:
    """Prequential calibrator. On save/load, every update is independently replayed."""

    def __init__(self):
        self.bias = [0.0, 0.0, 0.0]
        self.version = 0
        self.events: list[dict] = []
        self.forecasts: dict[str, Forecast] = {}
        self.receipts: dict[str, dict] = {}
        self._last_hash = "0"*64
        self._last_timestamp = None

    def predict(self, base_probs) -> tuple[float,float,float]:
        p = _probs(base_probs)
        logits = [log(p[i])+self.bias[i] for i in range(3)]
        shift = max(logits)
        weights = [exp(x-shift) for x in logits]
        denom = sum(weights)
        return tuple(x/denom for x in weights)

    def _append(self, kind: str, data: dict):
        payload = {"sequence":len(self.events)+1,"kind":kind,
                   "data":json.loads(_canonical(data)),"previous_sha256":self._last_hash}
        payload["sha256"] = _digest(payload)
        self.events.append(payload)
        self._last_hash = payload["sha256"]

    def register(self, item: Forecast):
        if not isinstance(item, Forecast):
            raise FeedbackError("forecast object required")
        if item.prediction_id in self.forecasts:
            if self.forecasts[item.prediction_id] == item:
                return
            raise FeedbackError("conflicting duplicate prediction")
        if item.learning_version != self.version:
            raise FeedbackError("forecast used stale learning version")
        if self._last_timestamp is not None and _datetime(item.forecast_utc) < self._last_timestamp:
            raise FeedbackError("forecast attempted after later settled event")
        if any(x.match_id == item.match_id for x in self.forecasts.values()):
            raise FeedbackError("duplicate fixture forecast")
        self.forecasts[item.prediction_id] = item
        self._last_timestamp = _datetime(item.forecast_utc)
        self._append("FORECAST", asdict(item))

    def settle(self, item: Settlement) -> dict:
        if not isinstance(item, Settlement):
            raise FeedbackError("settlement receipt required")
        original = self.forecasts.get(item.prediction_id)
        if original is None:
            raise FeedbackError("no precommitted forecast for settlement")
        existing = self.receipts.get(item.prediction_id)
        if existing is not None:
            if existing["settlement"] == asdict(item):
                return existing["receipt"]
            raise FeedbackError("conflicting or repeated settlement")
        if any(x["settlement"]["settlement_id"] == item.settlement_id for x in self.receipts.values()):
            raise FeedbackError("duplicate settlement identity")
        if original.source_sha256 != item.source_sha256:
            raise FeedbackError("settlement source does not match forecast")
        if _datetime(item.settled_utc) <= _datetime(original.forecast_utc):
            raise FeedbackError("settlement occurred before forecast")
        if self._last_timestamp is not None and _datetime(item.settled_utc) < self._last_timestamp:
            raise FeedbackError("settlement predates last journal event")
        # Simulated financial returns are NOT used as an input to training:
        # the actual settled categorical outcome is the feedback signal.
        pre = original.probabilities  # the already-published forecast, not a later revised probability
        won = original.selected_label == item.outcome_label
        pnl = round(item.stake * (item.decimal_odds-1) if won else -item.stake, 8)
        old = tuple(self.bias)
        self.bias = [max(-MAX_BIAS,min(MAX_BIAS,
                       (1-SHRINK)*old[i] - LEARNING_RATE*(pre[i]-(1.0 if i==item.outcome_label else 0.0))))
                     for i in range(3)]
        if not all(isfinite(x) for x in self.bias):
            raise FeedbackError("nonfinite learning state")
        self.version += 1
        receipt = {
            "prediction_id":item.prediction_id,
            "settlement_id":item.settlement_id,
            "forecast_sha256":_digest(asdict(original)),
            "outcome_label":item.outcome_label,
            "won":won,"virtual_pnl":pnl,
            "simulated_price_source":ODDS_SOURCE,
            "probability_loss_before_update":round(-log(max(pre[item.outcome_label],1e-15)),12),
            "learning_version":self.version,
            "bias_before":list(old),"bias_after":list(self.bias),
            "no_financial_execution":True,
        }
        self.receipts[item.prediction_id] = {"settlement":asdict(item),"receipt":receipt}
        self._last_timestamp = _datetime(item.settled_utc)
        self._append("SETTLEMENT",{"settlement":asdict(item),"receipt":receipt})
        return receipt

    def snapshot(self) -> dict:
        result={"schema":SCHEMA,"mode":"OFFLINE_HISTORICAL_LEARNING_ONLY",
                "learning_rate":LEARNING_RATE,"max_bias":MAX_BIAS,"shrink":SHRINK,
                "version":self.version,"bias":list(self.bias),
                "events":self.events,"last_event_sha256":self._last_hash,
                "last_event_utc":self._last_timestamp.isoformat() if self._last_timestamp else None,
                "no_live_execution":True,"no_provider_credentials":True}
        result["seal_sha256"] = _digest(result)
        return result

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "LossLearner":
        if not isinstance(snapshot,dict):
            raise FeedbackError("not a journal")
        sealed=dict(snapshot)
        digest=sealed.pop("seal_sha256",None)
        if digest != _digest(sealed) or sealed.get("schema") != SCHEMA:
            raise FeedbackError("sealed journal digest mismatch")
        if any(sealed.get(k)!=v for k,v in
               (("learning_rate",LEARNING_RATE),("max_bias",MAX_BIAS),
                ("shrink",SHRINK),("no_live_execution",True),
                ("no_provider_credentials",True))):
            raise FeedbackError("learning configuration modified")
        data=sealed.get("events")
        if not isinstance(data,list) or len(data)>100000:
            raise FeedbackError("event history outside bounds")
        instance=cls()
        for event in data:
            if not isinstance(event,dict):
                raise FeedbackError("malformed journal event")
            e=dict(event)
            chk=e.pop("sha256",None)
            if chk!=_digest(e) or e.get("previous_sha256")!=instance._last_hash or e.get("sequence")!=len(instance.events)+1:
                raise FeedbackError("journal hash chain mismatch")
            if e.get("kind")=="FORECAST":
                instance.register(Forecast(**e["data"]))
            elif e.get("kind")=="SETTLEMENT":
                details=e["data"]
                result=instance.settle(Settlement(**details["settlement"]))
                if result != details["receipt"]:
                    raise FeedbackError("settlement learning replay mismatch")
            else:
                raise FeedbackError("unrecognized event kind")
            if instance._last_hash!=chk:
                raise FeedbackError("replayed event differs")
        if instance.version!=sealed.get("version") or instance._last_hash!=sealed.get("last_event_sha256") or instance.bias!=sealed.get("bias") or (instance._last_timestamp.isoformat() if instance._last_timestamp else None)!=sealed.get("last_event_utc"):
            raise FeedbackError("replayed learning state mismatch")
        return instance


def write_immutable(path: Path,payload:dict):
    output=Path(path).resolve()
    if not output.parent.is_dir():
        raise FeedbackError("existing private evidence directory required")
    body=json.dumps(payload,indent=2,sort_keys=True,allow_nan=False)+"\n"
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as file:
        file.write(body)
        file.flush()
        os.fsync(file.fileno())
    return sha256(body.encode()).hexdigest()
