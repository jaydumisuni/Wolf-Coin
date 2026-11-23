"""Reproducible held-out 1X2 research baseline from CC0 match results.

No bookmaker odds, no execution, no strategy approval. All training fixtures
must precede all holdout fixtures; future results cannot influence predictions.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
from math import log
from pathlib import Path

from wolf_core.contracts import ContractError

OUTCOMES=("home","draw","away")


class ResearchBlocked(ContractError):
    pass


@dataclass(frozen=True)
class MatchResult:
    day: date
    home: str
    away: str
    outcome: str


@dataclass(frozen=True)
class Dataset:
    origin: str
    digest: str
    matches: tuple[MatchResult,...]


def ingest_results(path: str|Path, *, expected_sha256: str | None = None) -> Dataset:
    path=Path(path)
    blob=path.read_bytes()
    if len(blob)>250_000:
        raise ResearchBlocked("research dataset size exceeds bounded input")
    digest=sha256(blob).hexdigest()
    if expected_sha256 is not None and digest!=expected_sha256:
        raise ResearchBlocked("fixed input digest mismatch")
    try:
        payload=json.loads(blob)
    except (UnicodeDecodeError,ValueError) as exc:
        raise ResearchBlocked("invalid source JSON") from exc
    if not isinstance(payload,dict) or not isinstance(payload.get("matches"),list):
        raise ResearchBlocked("unrecognized source schema")
    matches=[]
    seen=set()
    for row in payload["matches"]:
        if not isinstance(row,dict):
            raise ResearchBlocked("invalid match record")
        try:
            day=date.fromisoformat(row["date"])
            home=row["team1"]; away=row["team2"]; raw=row["score"]
            score=raw.get("ft") if isinstance(raw,dict) else raw
            if (not isinstance(home,str) or not home.strip() or
                not isinstance(away,str) or not away.strip() or home==away or
                not isinstance(score,list) or len(score)!=2 or
                any(type(x) is not int or x<0 or x>50 for x in score)):
                raise ResearchBlocked("unverified final score or team identity")
        except (KeyError,TypeError,ValueError) as exc:
            raise ResearchBlocked("malformed historical match") from exc
        identity=(day,home,away)
        if identity in seen:
            raise ResearchBlocked("duplicate match identity")
        seen.add(identity)
        outcome="home" if score[0]>score[1] else "away" if score[0]<score[1] else "draw"
        matches.append(MatchResult(day,home,away,outcome))
    if len(matches)<20:
        raise ResearchBlocked("insufficient sample for even a research baseline")
    return Dataset(str(path),digest,tuple(sorted(matches,key=lambda x:(x.day,x.home,x.away))))


def _brier(prob: dict[str,float],actual:str) -> float:
    return sum((prob[o]-(1 if o==actual else 0))**2 for o in OUTCOMES)


def _log_loss(prob: dict[str,float],actual:str) -> float:
    return -log(prob[actual])


def evaluate_heldout(train:Dataset,holdout:Dataset,*,laplace:float=1.0)->dict:
    if train.digest==holdout.digest:
        raise ResearchBlocked("training and holdout use identical evidence")
    if max(x.day for x in train.matches)>=min(x.day for x in holdout.matches):
        raise ResearchBlocked("training dates overlap or precede holdout incorrectly")
    train_ids={(x.day,x.home,x.away) for x in train.matches}
    if train_ids & {(x.day,x.home,x.away) for x in holdout.matches}:
        raise ResearchBlocked("train/holdout identity overlap")
    if not isinstance(laplace,float) or not 0<laplace<=10:
        raise ResearchBlocked("invalid baseline smoothing")
    observed=Counter(x.outcome for x in train.matches)
    total=len(train.matches)+3*laplace
    baseline={o:(observed[o]+laplace)/total for o in OUTCOMES}
    uniform={o:1/3 for o in OUTCOMES}
    n=len(holdout.matches)
    count=Counter(x.outcome for x in holdout.matches)
    b=sum(_brier(baseline,x.outcome) for x in holdout.matches)/n
    ub=sum(_brier(uniform,x.outcome) for x in holdout.matches)/n
    loss=sum(_log_loss(baseline,x.outcome) for x in holdout.matches)/n
    uloss=sum(_log_loss(uniform,x.outcome) for x in holdout.matches)/n
    return {
        "schema":"wolf.heldout-baseline.v1",
        "train_hash":train.digest,"holdout_hash":holdout.digest,
        "train_count":len(train.matches),"holdout_count":n,
        "train_last_day":max(x.day for x in train.matches).isoformat(),
        "holdout_first_day":min(x.day for x in holdout.matches).isoformat(),
        "training_outcomes":dict(sorted(observed.items())),
        "heldout_outcomes":dict(sorted(count.items())),
        "probabilities":{k:round(v,8) for k,v in baseline.items()},
        "candidate_brier":round(b,8),"uniform_brier":round(ub,8),
        "candidate_log_loss":round(loss,8),"uniform_log_loss":round(uloss,8),
        "profit_qualified":False,"no_bookmaker_prices":True,
        "can_place_bets":False,
        "finding":"HISTORICAL_RESEARCH_ONLY_NOT_EVIDENCE_OF_POSITIVE_EXPECTED_VALUE"
    }
