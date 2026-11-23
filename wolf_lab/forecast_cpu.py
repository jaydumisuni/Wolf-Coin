"""Source-pinned deterministic CPU probability comparison, not a betting model.

Numpy softmax correction to bookmaker no-vig probabilities with only lagged
team features. The source dataset's historical *opening* quotes do not prove
those quotes were available to a real customer at prediction time.
No profit claim and no provider/funds integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Sequence

import numpy as np

from wolf_lab.learning_dataset import FeatureRow, FEATURE_NAMES

L2_CANDIDATES = (0.02,0.10,0.50)   # predeclared; no final-period tuning
MIN_BRIER_GAIN = 0.005
N_ITERATIONS = 550
RATE = 0.1


@dataclass(frozen=True)
class Fit:
    name: str
    penalty: float
    weights: tuple[tuple[float,...],...]

    def predict(self, rows: Sequence[FeatureRow]) -> np.ndarray:
        w=np.asarray(self.weights,dtype=np.float64)
        features,market,_=_matrix(rows)
        logits=np.log(np.maximum(market,1e-12))+features @ w
        logits-=logits.max(axis=1,keepdims=True)
        score=np.exp(logits)
        return score/score.sum(axis=1,keepdims=True)


def _matrix(rows: Sequence[FeatureRow]):
    if not rows:
        raise ValueError("empty evaluation partition")
    x=np.asarray([r.features for r in rows],dtype=np.float64)
    market=np.asarray([r.market for r in rows],dtype=np.float64)
    y=np.asarray([r.label for r in rows],dtype=np.int64)
    if x.ndim != 2 or x.shape[1]!=len(FEATURE_NAMES):
        raise ValueError("unexpected lagged feature shape")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(market)):
        raise ValueError("non-finite research input")
    if np.any(market<=0) or not np.allclose(market.sum(axis=1),1,atol=1e-8):
        raise ValueError("invalid market probabilities")
    if np.any(y<0) or np.any(y>2):
        raise ValueError("invalid target label")
    return x,market,y


def fit(train: Sequence[FeatureRow], penalty: float) -> Fit:
    if penalty not in L2_CANDIDATES:
        raise ValueError("non-predeclared regularization")
    x,market,y=_matrix(train)
    n,d=x.shape
    weights=np.zeros((d,3),dtype=np.float64)
    goal=np.zeros((n,3),dtype=np.float64)
    goal[np.arange(n),y]=1.0
    for _ in range(N_ITERATIONS):
        logits=np.log(market)+x @ weights
        logits-=np.max(logits,axis=1,keepdims=True)
        probs=np.exp(logits)
        probs/=probs.sum(axis=1,keepdims=True)
        grad=x.T @ (probs-goal)/n + penalty*weights
        weights-=RATE*grad
    if not np.all(np.isfinite(weights)):
        raise ValueError("diverged CPU training")
    return Fit("market-offset-softmax-lagged",penalty,
               tuple(tuple(float(z) for z in row) for row in weights))


def scores(predictions: np.ndarray, rows: Sequence[FeatureRow]) -> dict[str,float]:
    x,_,y=_matrix(rows)
    if predictions.shape!=(len(rows),3):
        raise ValueError("prediction dimensions differ from fixtures")
    if not np.all(np.isfinite(predictions)) or np.any(predictions<=0):
        raise ValueError("invalid predicted probabilities")
    if not np.allclose(predictions.sum(axis=1),1,atol=1e-8):
        raise ValueError("predictions not normalized")
    onehot=np.zeros_like(predictions)
    onehot[np.arange(len(rows)),y]=1.0
    brier=np.mean(np.sum((predictions-onehot)**2,axis=1))
    logloss=-np.mean(np.log(np.maximum(predictions[np.arange(len(rows)),y],1e-12)))
    return {"brier":round(float(brier),9),"log_loss":round(float(logloss),9)}


def compare(train:Sequence[FeatureRow], validation:Sequence[FeatureRow],
            diagnostic:Sequence[FeatureRow]) -> dict:
    trainmax=max(r.day for r in train)
    validmin=min(r.day for r in validation)
    validmax=max(r.day for r in validation)
    diagnosticmin=min(r.day for r in diagnostic)
    if not trainmax < validmin or not validmax < diagnosticmin:
        raise ValueError("time partitions overlap or reverse")
    market_scores=scores(np.asarray([r.market for r in validation]),validation)
    candidates=[]
    for p in L2_CANDIDATES:
        model=fit(train,p)
        vals=scores(model.predict(validation),validation)
        candidates.append({"penalty":p,"scores":vals,"model":model})
    best=min(candidates,key=lambda c:(c["scores"]["brier"],c["scores"]["log_loss"],c["penalty"]))
    best_scores=best["scores"]
    improvement=market_scores["brier"]-best_scores["brier"]
    eligible=(improvement>=MIN_BRIER_GAIN and
              best_scores["log_loss"]<market_scores["log_loss"])
    baseline_diagnostic=scores(np.asarray([r.market for r in diagnostic]),diagnostic)
    if eligible:
        selected=best["model"]
        predicted=scores(selected.predict(diagnostic),diagnostic)
    else:
        # This is an informative, already-exposed diagnostic, NOT a fresh
        # holdout. No model is allowed for paper selections on this branch.
        predicted=baseline_diagnostic
    return {
        "schema":"wolf.lagged-features-market-cpu.v1",
        "mode":"PRIVATE_RESEARCH_ONLY",
        "feature_names":list(FEATURE_NAMES),
        "training_rows":len(train),
        "validation_rows":len(validation),
        "exposed_diagnostic_rows":len(diagnostic),
        "training_end":trainmax,
        "validation_start":validmin,
        "validation_end":validmax,
        "exposed_diagnostic_start":diagnosticmin,
        "market_validation_scores":market_scores,
        "candidate_validation_scores":[{"l2":c["penalty"],**c["scores"]} for c in candidates],
        "minimum_brier_gain":MIN_BRIER_GAIN,
        "best_candidate_penalty":best["penalty"],
        "best_candidate_brier_gain":round(improvement,9),
        "selected":eligible,
        "decision":"CANDIDATE_RESEARCH_ONLY" if eligible else "ABSTAIN_NO_VALIDATED_FORECAST_EDGE",
        "exposed_diagnostic_scores":predicted,
        "exposed_market_scores":baseline_diagnostic,
        "final_unexamined_period_included":False,
        "profit_proven":False,
        "live_ready":False,
        "no_paper_or_real_orders":True,
        "limitations":[
            "2025/26 was already inspected by earlier Wolf-Coin research and cannot be called a clean unseen period.",
            "Football-Data quotes lack certified per-account, per-match availability timestamps.",
            "Validation model fitting improves calibration only if held-out proper scoring improves; this cannot establish trade profitability.",
            "Three small regularized CPU configurations and fixed lag features, no neural SUP-Bit model training."
        ],
    }
