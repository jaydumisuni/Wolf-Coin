"""Three-window, predeclared validation and final evaluation for Wolf-Coin.

Selection criterion is proper scoring on the validation window, never ROI.
If no out-of-sample calibration improvement over market appears, abstain.
The final window is evaluated once after selecting the candidate, and cannot
be used to select/adjust the same model generation.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import json
from typing import Any

from wolf_core.contracts import money
from .odds_replay import (
    OddsSeason, ReplayRefused, ReplayPolicy, EloResearchModel,
    _by_day, _no_vig, _proper_score, _rounded_stake, OUTCOMES, _train
)

# Frozen before inspecting the final period. Choosing by Brier, not ROI.
BLEND_WEIGHTS = (0.0, 0.2, 0.4, 0.6, 1.0)
MIN_BRIER_IMPROVEMENT = 0.005
MAX_PRICE = Decimal("5.0")


def _chronology(train: OddsSeason, validation: OddsSeason, final: OddsSeason) -> None:
    dates = [(x.matches[0].day, x.matches[-1].day) for x in (train,validation,final)]
    digests = {train.digest,validation.digest,final.digest}
    if len(digests) != 3 or not (dates[0][1] < dates[1][0] and dates[1][1] < dates[2][0]):
        raise ReplayRefused("train, validation and final must be separate chronological periods")
    if min(len(x.matches) for x in (train,validation,final)) < 50:
        raise ReplayRefused("insufficient matches in one of three disjoint periods")
    keys = set()
    for dataset in (train,validation,final):
        for m in dataset.matches:
            if m.key in keys:
                raise ReplayRefused("duplicate match across research partitions")
            keys.add(m.key)


def _mix(elo: dict[str,float], market: dict[str,float], weight: float) -> dict[str,float]:
    return {o:(1-weight)*market[o]+weight*elo[o] for o in OUTCOMES}


def _validate(train:OddsSeason, validation:OddsSeason, policy:ReplayPolicy):
    model = _train(train, policy)
    brier = {w:0.0 for w in BLEND_WEIGHTS}
    market = 0.0
    for day in _by_day(validation.matches):
        for m in day:
            pred=model.prediction(m)
            benchmark=_no_vig(m)
            market+=_proper_score(benchmark,m.result)
            for w in BLEND_WEIGHTS:
                brier[w]+=_proper_score(_mix(pred,benchmark,w),m.result)
        model.learn_after_day(day)
    market/=len(validation.matches)
    scored={w:brier[w]/len(validation.matches) for w in BLEND_WEIGHTS}
    # Strict deterministic tie break: least exposed to uncalibrated model.
    best=min(BLEND_WEIGHTS,key=lambda w:(round(scored[w],12),w))
    better=market-scored[best]>=MIN_BRIER_IMPROVEMENT and best>0.0
    return best if better else None, market, scored


def _refit(train:OddsSeason, validation:OddsSeason, policy:ReplayPolicy):
    all_matches=tuple(sorted(train.matches+validation.matches,key=lambda m:m.key))
    count=sum(m.result=="D" for m in all_matches)
    draw=max(policy.draw_probability_min,min(policy.draw_probability_max,count/len(all_matches)))
    model=EloResearchModel(policy.home_elo_bonus,policy.elo_step,draw)
    for day in _by_day(all_matches):
        model.learn_after_day(day)
    return model


def _test(model:EloResearchModel,final:OddsSeason,weight:float|None,policy:ReplayPolicy) -> dict:
    bankroll=policy.starting_bankroll
    peak=bankroll
    max_dd=Decimal("0")
    wagered=Decimal("0")
    gain=Decimal("0")
    wins=0
    bets=0
    abstained=0
    count_days=0
    scores=0.0
    market_scores=0.0
    ledger=[]
    for day in _by_day(final.matches):
        count_days+=1
        offers=[]
        for m in day:
            baseline=_no_vig(m)
            current=model.prediction(m)
            candidate=baseline if weight is None else _mix(current,baseline,weight)
            market_scores+=_proper_score(baseline,m.result)
            scores+=_proper_score(candidate,m.result)
            if weight is None:
                continue
            for k,o in enumerate(OUTCOMES):
                quote=m.prices[k]
                if quote>MAX_PRICE:
                    continue
                expected=Decimal(str(candidate[o]))*quote - Decimal("1")
                if expected>policy.min_expected_value:
                    offers.append((expected,m.key,o,quote,m.result))
        offers.sort(key=lambda x:(-x[0],x[1],x[2]))
        stake=_rounded_stake(bankroll,policy)
        if not offers or stake<=0:
            abstained+=1
        else:
            expected,identity,selection,price,actual=offers[0]
            won=selection==actual
            gross=stake*(price-Decimal(1)) if won else -stake
            net=gross-max(gross,Decimal(0))*policy.hypothetical_win_commission
            bankroll+=net
            gain+=net
            wagered+=stake
            bets+=1
            wins+=int(won)
            peak=max(peak,bankroll)
            max_dd=max(max_dd,(peak-bankroll)/peak)
            ledger.append({
                "date":identity[0],"match":f"{identity[1]} vs {identity[2]}",
                "selection":selection,"outcome":actual,
                "offered_opening_odds":str(price),"stake_virtual_ZMW":str(stake),
                "estimated_ev":str(expected.quantize(Decimal("0.0001"))),
                "net_virtual_ZMW":str(net.quantize(Decimal("0.000001"))),
                "balance_virtual_ZMW":str(bankroll.quantize(Decimal("0.000001"))),
                "won":won
            })
        model.learn_after_day(day)
    n=len(final.matches)
    return {
        "bets":bets,"wins":wins,"holdout_days":count_days,"abstained_days":abstained,
        "initial_virtual_ZMW":str(policy.starting_bankroll),
        "final_virtual_ZMW":str(bankroll.quantize(Decimal("0.000001"))),
        "net_virtual_ZMW":str(gain.quantize(Decimal("0.000001"))),
        "total_wagered_virtual_ZMW":str(wagered),
        "ROI_on_wagers_percent":str((gain/wagered*100).quantize(Decimal("0.01"))) if wagered else None,
        "max_drawdown_percent":str((max_dd*100).quantize(Decimal("0.01"))),
        "candidate_brier":round(scores/n,6),
        "market_brier":round(market_scores/n,6),
        "candidate_brier_better_than_market": scores < market_scores,
        "ledger":ledger,
    }


def walk_forward(train:OddsSeason,validation:OddsSeason,final:OddsSeason,
                 *,policy:ReplayPolicy=ReplayPolicy()) -> dict:
    _chronology(train,validation,final)
    selected,market_brier,scores=_validate(train,validation,policy)
    model=_refit(train,validation,policy)
    final_score=_test(model,final,selected,policy)
    return {
        "schema":"wolf.walk-forward-three-window.v1",
        "mode":"PRIVATE_HISTORICAL_PAPER_RESEARCH",
        "train_sha256":train.digest,"validation_sha256":validation.digest,
        "final_sha256":final.digest,
        "train_matches":len(train.matches),"validation_matches":len(validation.matches),
        "final_matches":len(final.matches),
        "training_end":train.matches[-1].day.isoformat(),
        "validation_end":validation.matches[-1].day.isoformat(),
        "final_start":final.matches[0].day.isoformat(),
        "final_end":final.matches[-1].day.isoformat(),
        "criterion":"validation 1X2 Brier beats de-vigged market by at least 0.005",
        "candidate_weights":list(BLEND_WEIGHTS),
        "validation_brier":{str(w):round(score,6) for w,score in scores.items()},
        "validation_market_brier":round(market_brier,6),
        "minimum_brier_improvement":MIN_BRIER_IMPROVEMENT,
        "selected_blend_weight":selected,
        "decision":"MODEL_ADMITTED_TO_HISTORICAL_TEST" if selected is not None else "ABSTAIN_NO_VALIDATED_FORECAST_EDGE",
        "final":final_score,
        "future_profit_proven":False,
        "live_admission":False,
        "license_note":"Research-only local historical datasets; do not publish raw source CSVs.",
        "limitations":[
            "Quoted historical opening prices are not verified actionable quotes or legal provider permission.",
            "No real-world fills, accepted stake minimums, withdrawals or transaction evidence.",
            "One holdout season cannot establish a repeatable future edge.",
            "Training/validation/final partitions are historical and subject to competition drift.",
            "Model candidates and selection criterion frozen before opening final period."
        ],
    }


def render_walkforward_html(report: dict) -> str:
    """Offline, static results. No live trading or interactive execution."""
    from html import escape
    def e(value): return escape(str(value), quote=True)
    final=report["final"]
    raw = report["selected_blend_weight"]
    choice = "NO MODEL ADMITTED — NO BETS" if raw is None else f"Validation-selected ELO blend: {raw}"
    rows="".join(
        "<tr>"+"".join("<td>"+e(x[key])+"</td>" for key in
            ("date","match","selection","outcome","offered_opening_odds",
             "stake_virtual_ZMW","net_virtual_ZMW","balance_virtual_ZMW"))+"</tr>"
        for x in final["ledger"]
    )
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wolf-Coin / Walk-forward proof</title>
<style>
body{{background:#0d1628;color:#e6f0ff;font:15px system-ui;margin:auto;max-width:1100px;padding:24px}}
h1{{color:#9be5ff}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}
.card{{background:#172640;border:1px solid #354b6b;border-radius:14px;padding:20px;margin:16px 0}}
small{{color:#9baecb}}strong{{font-size:24px}}.warning{{color:#ffd591}}
table{{border-collapse:collapse;display:block;overflow-x:auto}}td,th{{padding:9px 12px;border-bottom:1px solid #334764;white-space:nowrap;text-align:left}}
</style></head><body>
<h1>Wolf-Coin / Walk-forward lab</h1>
<p class="warning">Research-only · No real money execution · No claim of proven profitability</p>
<section class="card"><h2>{e(choice)}</h2>
<p>Training {e(report["train_matches"])} · Validation {e(report["validation_matches"])} · Fresh final {e(report["final_matches"])} fixtures</p>
<p>Validation market Brier {e(report["validation_market_brier"])} · Model must improve by {e(report["minimum_brier_improvement"])} or abstain.</p></section>
<div class="grid">
<div class="card"><small>Virtual ending balance</small><p><strong>K{e(final["final_virtual_ZMW"])}</strong></p></div>
<div class="card"><small>Virtual net gain/loss</small><p><strong>K{e(final["net_virtual_ZMW"])}</strong></p></div>
<div class="card"><small>Paper selections</small><p><strong>{e(final["bets"])}</strong></p></div>
<div class="card"><small>Model/market final Brier</small><p><strong>{e(final["candidate_brier"])} / {e(final["market_brier"])}</strong></p></div>
</div>
<section class="card"><h2>Chronological paper decisions</h2>
<table><thead><tr><th>Date</th><th>Match</th><th>Selection</th><th>Actual</th>
<th>Opening odds</th><th>Stake K</th><th>Net K</th><th>Balance K</th></tr></thead>
<tbody>{rows}</tbody></table></section>
<section class="card"><h2>Evidence</h2>
<p><small>Training SHA-256: {e(report["train_sha256"])}</small></p>
<p><small>Validation SHA-256: {e(report["validation_sha256"])}</small></p>
<p><small>Final SHA-256: {e(report["final_sha256"])}</small></p></section>
<p class="warning">Historical quoted prices are not proof of obtainable bookmaker prices. No live provider or capital was used.</p>
</body></html>"""
