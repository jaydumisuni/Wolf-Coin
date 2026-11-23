"""Small fully deterministic CPU-only tabular models for CC0 football results.

Offline NumPy only; fixed training configuration, no hidden search,
source-owned odds, provider credentials or financial actions. MLP implementation
is separate from SUP-Bit: SUP-Bit has not been qualified for this task.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from typing import Sequence
from wolf_lab.cc0_training import Example, FEATURES

SEED = 17
LEARNING_RATE = 0.07
ITERATIONS = 350
HIDDEN = 8
L2 = 0.015
MIN_BRIER_GAIN = 0.012
MIN_LOG_LOSS_GAIN = 0.005
KINDS = ("linear","mlp")
SOURCE_MODEL_VERSION = "wolf.cc0-numpy-mlp.v1"


class MLPError(ValueError): pass


def _arrays(rows: Sequence[Example]):
    if not rows:raise MLPError("empty corpus")
    x=np.asarray([r.features for r in rows],dtype=np.float64)
    y=np.asarray([r.label for r in rows],dtype=object)
    if x.ndim!=2 or x.shape[1]!=len(FEATURES) or not np.all(np.isfinite(x)):
        raise MLPError("feature shape or nonfinite data")
    if not all(v is None or (type(v) is int and 0<=v<3) for v in y):
        raise MLPError("invalid three-way label")
    return x,y


def _prob(logits):
    values=logits-np.max(logits,axis=1,keepdims=True)
    e=np.exp(values)
    return e/e.sum(axis=1,keepdims=True)


def proper(y: np.ndarray,p: np.ndarray) -> dict[str,float]:
    if y.ndim!=1 or p.shape!=(len(y),3) or len(y)==0:
        raise MLPError("score array shape mismatch")
    if any(type(v) is not int and not isinstance(v,np.integer) for v in y):
        raise MLPError("cannot score unplayed fixtures")
    if not np.all(np.isfinite(p)) or np.any(p<=0) or not np.allclose(p.sum(axis=1),1,atol=1e-8):
        raise MLPError("invalid prediction probabilities")
    labels=y.astype(np.int64)
    if np.any(labels<0) or np.any(labels>=3):raise MLPError("label outside 1X2")
    target=np.eye(3)[labels]
    return {"brier":round(float(np.mean(np.sum((p-target)**2,axis=1))),9),
            "log_loss":round(float(np.mean(-np.log(np.clip(p[np.arange(len(y)),labels],1e-12,1)))),9)}


@dataclass(frozen=True)
class Model:
    kind:str
    mean:tuple[float,...]
    scale:tuple[float,...]
    a:tuple[tuple[float,...],...]
    b:tuple[float,...]
    c:tuple[tuple[float,...],...] | None
    d:tuple[float,...] | None
    def predict(self,rows:Sequence[Example])->np.ndarray:
        x,_=_arrays(rows)
        mean=np.asarray(self.mean)
        scale=np.asarray(self.scale)
        z=(x-mean)/scale
        out=z@np.asarray(self.a)+np.asarray(self.b)
        if self.kind=="mlp":
            hidden=np.tanh(out)
            out=hidden@np.asarray(self.c)+np.asarray(self.d)
        return _prob(out)


def fit(train: Sequence[Example],kind: str) -> Model:
    if kind not in KINDS:raise MLPError("non-predeclared architecture")
    x,labels=_arrays(train)
    if any(v is None for v in labels):
        raise MLPError("unscored fixtures cannot train model")
    y=labels.astype(np.int64)
    if len(y)<400:
        raise MLPError("insufficient training records")
    counts=np.bincount(y,minlength=3)
    prior=(counts+1)/(len(y)+3)
    mu=x.mean(axis=0)
    scale=x.std(axis=0)
    scale[scale<0.001]=1
    x=(x-mu)/scale
    target=np.eye(3)[y]
    rng=np.random.default_rng(SEED)
    if kind=="linear":
        a=np.zeros((x.shape[1],3),dtype=np.float64)
        b=np.log(prior)
        for _ in range(ITERATIONS):
            proba=_prob(x@a+b)
            grad=(proba-target)/len(y)
            a-=LEARNING_RATE*(x.T@grad+L2*a)
            b-=LEARNING_RATE*grad.sum(axis=0)
        return Model(kind,tuple(mu),tuple(scale),tuple(map(tuple,a)),tuple(b),None,None)
    a=rng.normal(0,0.1,size=(x.shape[1],HIDDEN))
    b=np.zeros(HIDDEN,dtype=np.float64)
    c=rng.normal(0,0.1,size=(HIDDEN,3))
    d=np.log(prior)
    for _ in range(ITERATIONS):
        h=np.tanh(x@a+b)
        proba=_prob(h@c+d)
        grad=(proba-target)/len(y)
        gc=h.T@grad+L2*c
        gd=grad.sum(axis=0)
        upstream=(grad@c.T)*(1-h*h)
        ga=x.T@upstream+L2*a
        gb=upstream.sum(axis=0)
        a-=LEARNING_RATE*ga
        b-=LEARNING_RATE*gb
        c-=LEARNING_RATE*gc
        d-=LEARNING_RATE*gd
    return Model(kind,tuple(mu),tuple(scale),tuple(map(tuple,a)),
                 tuple(b),tuple(map(tuple,c)),tuple(d))


def validated_comparison(train:Sequence[Example], validation:Sequence[Example])->dict:
    if not train or not validation or max(r.key[0] for r in train)>=min(r.key[0] for r in validation):
        raise MLPError("train and validation must be disjoint in time")
    _,y_train=_arrays(train)
    _,y_val=_arrays(validation)
    if any(x is None for x in y_val):
        raise MLPError("validation has missing results")
    count=np.bincount(y_train.astype(np.int64),minlength=3)
    prior=(count+1)/(len(y_train)+3)
    benchmark=np.tile(prior,(len(validation),1))
    baseline=proper(y_val,benchmark)
    methods={}
    for kind in KINDS:
        model=fit(train,kind)
        metric=proper(y_val,model.predict(validation))
        methods[kind]={"model":model,"metrics":metric}
    best=min(KINDS,key=lambda k:(methods[k]["metrics"]["brier"],
                                  methods[k]["metrics"]["log_loss"],k))
    x=methods[best]["metrics"]
    qualifies=(baseline["brier"]-x["brier"]>=MIN_BRIER_GAIN
               and baseline["log_loss"]-x["log_loss"]>=MIN_LOG_LOSS_GAIN)
    return {
        "schema":SOURCE_MODEL_VERSION,
        "train_rows":len(train),"validation_rows":len(validation),
        "train_end":max(r.key[0] for r in train),
        "validation_start":min(r.key[0] for r in validation),
        "seed":SEED,"iterations":ITERATIONS,"learning_rate":LEARNING_RATE,
        "hidden_units":HIDDEN,"l2":L2,"candidate_kinds":list(KINDS),
        "baseline":{"method":"training-class-prior-only",**baseline},
        "candidates":{k:methods[k]["metrics"] for k in KINDS},
        "selected_kind":best if qualifies else None,
        "selection_criterion":"Brier improvement >= 0.012 and log-loss improvement >= 0.005 versus training class prior on validation",
        "decision":"MODEL_QUALIFIED_FOR_FRESH_SCORE_ONLY" if qualifies else "ABSTAIN_NO_VALIDATED_FORECAST_IMPROVEMENT",
        "result_never_exposed_to_training":True,
        "financial_edge_proven":False,
        "live_admission":False,
    }


def selected_model(train:Sequence[Example],decision:dict)->Model|None:
    kind=decision.get("selected_kind")
    if kind is None:return None
    if kind not in KINDS:raise MLPError("unrecognized model")
    return fit(train,kind)
