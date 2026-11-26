"""Pre-live, source-hash-bound feedback from settled historical outcomes.

Separates prediction (an odds-only, no-label interface) from later settlement.
No provider credentials, trading API, funded action, SUP approval or deployment
authority. This is a retrospective diagnostic, not an untouched holdout.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import argparse
import json
import math
import os
import random
import sys
from typing import Sequence

from wolf_lab.odds_replay import (
    OddsMatch, OddsSeason, ReplayPolicy, ReplayRefused,
    _train, _by_day, _no_vig, _proper_score, _rounded_stake, OUTCOMES,
)

SCHEMA = "wolf.prelive-settlement-feedback.v1"
SOURCES = {
    "2022-23": "8442792d3b614c94ea3cf381bd2736805889cc1713169035368fff19c3d02380",
    "2023-24": "b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3",
    "2024-25": "d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4",
    "2025-26": "3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62",
}
FOLDS = (("2022-23", "2023-24"), ("2023-24", "2024-25"), ("2024-25", "2025-26"))
BOOTSTRAP_SEED = 20261126
BOOTSTRAP_REPS = 2000
MIN_BRIER_EDGE = 0.005
MIN_PAPER_DECISIONS = 200
MAX_DRAWDOWN_FRACTION = Decimal("0.20")
MAX_QUOTE = Decimal("5")
NO_AUTHORITY = "NO_REAL_MONEY_OR_PROVIDER_AUTHORITY"


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value) -> str:
    return sha256(_json(value)).hexdigest()


def _key(day: date, home: str, away: str) -> str:
    return f"{day.isoformat()}|{home}|{away}"


def _state_sha(model) -> str:
    return _sha({"ratings": sorted(model.ratings.items()),
                 "draw_probability": model.draw_probability})


@dataclass(frozen=True)
class PreMatchOffer:
    day: date
    home: str
    away: str
    prices: tuple[Decimal, Decimal, Decimal]

    def __post_init__(self):
        if not isinstance(self.day, date) or type(self.home) is not str or type(self.away) is not str:
            raise ReplayRefused("invalid pre-match identity")
        if not self.home.strip() or not self.away.strip() or self.home == self.away:
            raise ReplayRefused("invalid pre-match teams")
        if (len(self.prices) != 3 or
            any(not isinstance(x, Decimal) or not x.is_finite() or x <= 1 or x > 1000
                for x in self.prices)):
            raise ReplayRefused("invalid pre-match prices")

    @property
    def identity(self):
        return _key(self.day, self.home, self.away)


@dataclass(frozen=True)
class SettledResult:
    identity: str
    outcome: str
    observed_day: date
    source_sha256: str

    def __post_init__(self):
        if type(self.identity) is not str or self.identity.count("|") != 2:
            raise ReplayRefused("unrecognized settled identity")
        if self.outcome not in OUTCOMES or not isinstance(self.observed_day, date):
            raise ReplayRefused("unrecognized final result or observation day")
        if type(self.source_sha256) is not str or len(self.source_sha256) != 64 or any(
            x not in "0123456789abcdef" for x in self.source_sha256
        ):
            raise ReplayRefused("independent source digest required")


def verify_journal(entries: list[dict]) -> str:
    """Verify every SHA-linked entry including order, contents and predecessor."""
    previous = "0" * 64
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {
            "sequence", "kind", "previous_sha256", "body", "entry_sha256"
        } or entry["sequence"] != i or entry["previous_sha256"] != previous:
            raise ReplayRefused("journal sequence or previous hash mismatch")
        expected = _sha({key: entry[key] for key in (
            "sequence", "kind", "previous_sha256", "body"
        )})
        if entry["entry_sha256"] != expected:
            raise ReplayRefused("journal hash mismatch")
        previous = expected
    return previous


class PreliveFeedback:
    """One-off paper shadow; all real settlement methods deliberately absent."""

    def __init__(self, train: OddsSeason, holdout_digest: str, *,
                 policy: ReplayPolicy = ReplayPolicy()):
        if not train.matches or len(train.matches) < 300 or type(holdout_digest) is not str:
            raise ReplayRefused("qualified train and holdout digest required")
        if train.digest == holdout_digest or len(holdout_digest) != 64:
            raise ReplayRefused("training and settlement source may not coincide")
        self.train_end = train.matches[-1].day
        self.holdout_digest = holdout_digest
        self.model = _train(train, policy)
        self.control = _train(train, policy)
        self.control_sha = _state_sha(self.control)
        self.policy = policy
        self.bankroll = policy.starting_bankroll
        self.peak = self.bankroll
        self.max_drawdown = Decimal("0")
        self.pending: dict | None = None
        self.last_settled_day = self.train_end
        self.seen: set[str] = set()
        self.journal: list[dict] = []
        self.day_scores: list[dict] = []
        self.wagers: list[dict] = []
        self.forecast_errors = 0
        self.loss_day_updates = 0
        self.update_days = 0

    def _record(self, kind: str, body: dict):
        previous = self.journal[-1]["entry_sha256"] if self.journal else "0" * 64
        item = {
            "sequence": len(self.journal), "kind": kind,
            "previous_sha256": previous, "body": body,
        }
        item["entry_sha256"] = _sha(item)
        self.journal.append(item)

    def prepare_day(self, offers: Sequence[PreMatchOffer]) -> dict:
        if self.pending is not None:
            raise ReplayRefused("existing predictions must settle before another date")
        if not offers or len(offers) > 20 or any(type(x) is not PreMatchOffer for x in offers):
            raise ReplayRefused("bounded pre-match offer batch required")
        day = offers[0].day
        if any(x.day != day for x in offers) or day <= self.last_settled_day:
            raise ReplayRefused("pre-match dates must strictly increase")
        ids = [x.identity for x in offers]
        if len(ids) != len(set(ids)) or set(ids) & self.seen:
            raise ReplayRefused("duplicate or replayed pre-match identity")
        predictions = []
        candidates = []
        for x in sorted(offers, key=lambda t: t.identity):
            # OddsMatch is constructed only with a dummy label in this
            # prediction-only method; that label is never consulted.
            neutral = OddsMatch(x.day, x.home, x.away, "D", x.prices)
            adaptive = self.model.prediction(neutral)
            frozen = self.control.prediction(neutral)
            market = _no_vig(neutral)
            probabilities = [adaptive[o] for o in OUTCOMES]
            predictions.append({
                "identity": x.identity,
                "prices": [str(v) for v in x.prices],
                "adaptive": probabilities,
                "frozen": [frozen[o] for o in OUTCOMES],
                "market": [market[o] for o in OUTCOMES],
            })
            for i, outcome in enumerate(OUTCOMES):
                price = x.prices[i]
                if price > MAX_QUOTE:
                    continue
                expected = Decimal(str(probabilities[i])) * price - Decimal("1")
                if expected > self.policy.min_expected_value:
                    candidates.append((expected, x.identity, outcome, price))
        candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
        stake = _rounded_stake(self.bankroll, self.policy)
        shadow = None
        if candidates and stake > 0:
            ev, identity, side, price = candidates[0]
            shadow = {
                "identity": identity, "selection": side,
                "quoted_opening_odds": str(price),
                "estimated_ev": str(ev),
                "stake_virtual_ZMW": str(stake),
            }
        sealed = {
            "date": day.isoformat(), "predictions": predictions,
            "paper_decision": shadow, "model_sha256": _state_sha(self.model),
            "control_sha256": self.control_sha,
            "holdout_sha256": self.holdout_digest,
        }
        self._record("predictions_frozen_before_outcomes", sealed)
        self.pending = sealed
        return json.loads(_json(sealed))

    def settle_day(self, receipts: Sequence[SettledResult]) -> dict:
        if self.pending is None:
            raise ReplayRefused("cannot settle before prediction freeze")
        predictions = self.pending["predictions"]
        pending_ids = {x["identity"] for x in predictions}
        if not isinstance(receipts, (list, tuple)) or not all(
            type(x) is SettledResult for x in receipts
        ):
            raise ReplayRefused("typed settlement receipts required")
        identities = [x.identity for x in receipts]
        if len(identities) != len(set(identities)) or set(identities) != pending_ids:
            raise ReplayRefused("settlement coverage missing, repeated or unknown")
        predicted_day = date.fromisoformat(self.pending["date"])
        if any(x.source_sha256 != self.holdout_digest or x.observed_day <= predicted_day
               for x in receipts):
            raise ReplayRefused("settlement not later than prediction, or digest mismatch")
        outcomes = {x.identity: x.outcome for x in receipts}
        score = {"adaptive": 0.0, "market": 0.0, "frozen": 0.0}
        errors = 0
        training = []
        for forecast in predictions:
            actual = outcomes[forecast["identity"]]
            for method in score:
                score[method] += _proper_score(
                    dict(zip(OUTCOMES, forecast[method])), actual
                )
            errors += int(OUTCOMES[max(range(3),
                                  key=lambda i: forecast["adaptive"][i])] != actual)
            identity = forecast["identity"].split("|")
            training.append(OddsMatch(
                date.fromisoformat(identity[0]), identity[1], identity[2],
                actual, tuple(Decimal(x) for x in forecast["prices"])
            ))
        shadow = self.pending["paper_decision"]
        paper = None
        if shadow is not None:
            won = shadow["selection"] == outcomes[shadow["identity"]]
            stake = Decimal(shadow["stake_virtual_ZMW"])
            quote = Decimal(shadow["quoted_opening_odds"])
            gross = stake * (quote - Decimal(1)) if won else -stake
            commission = (gross if gross > 0 else Decimal(0)) * self.policy.hypothetical_win_commission
            net = gross - commission
            self.bankroll += net
            self.peak = max(self.bankroll, self.peak)
            self.max_drawdown = max(self.max_drawdown, (self.peak-self.bankroll)/self.peak)
            paper = {**shadow, "won": won, "virtual_net_ZMW": str(net),
                     "virtual_balance_ZMW": str(self.bankroll)}
            self.wagers.append(paper)
        previous_sha = _state_sha(self.model)
        self.model.learn_after_day(training)
        after_sha = _state_sha(self.model)
        # The frozen control must never see a post-train outcome.
        if _state_sha(self.control) != self.control_sha:
            raise ReplayRefused("frozen control was contaminated by a result")
        if previous_sha != after_sha:
            self.update_days += 1
            if errors or (paper is not None and not paper["won"]):
                self.loss_day_updates += 1
        self.forecast_errors += errors
        n = len(predictions)
        scored = {
            "date": predicted_day.isoformat(), "matches": n,
            "adaptive_brier": score["adaptive"]/n,
            "market_brier": score["market"]/n,
            "frozen_brier": score["frozen"]/n,
            "market_minus_adaptive_sum": score["market"]-score["adaptive"],
            "prediction_misses": errors, "paper": paper,
            "model_sha256_before": previous_sha, "model_sha256_after": after_sha,
            "receipt_source_sha256": self.holdout_digest,
            "settlement_receipts": [
                {"identity": receipt.identity, "outcome": receipt.outcome,
                 "observed_day": receipt.observed_day.isoformat(),
                 "source_sha256": receipt.source_sha256}
                for receipt in sorted(receipts, key=lambda x: x.identity)
            ],
        }
        self._record("settled_then_updated", scored)
        self.day_scores.append(scored)
        self.seen.update(pending_ids)
        self.last_settled_day = predicted_day
        self.pending = None
        return json.loads(_json(scored))

    def report(self) -> dict:
        if self.pending is not None or not self.day_scores:
            raise ReplayRefused("cannot report an unfinished replay")
        n = sum(x["matches"] for x in self.day_scores)
        def mean(key):
            return sum(x[key] * x["matches"] for x in self.day_scores) / n
        wagered = sum((Decimal(x["stake_virtual_ZMW"]) for x in self.wagers), Decimal(0))
        net = self.bankroll - self.policy.starting_bankroll
        return {
            "scored_matches": n, "scored_days": len(self.day_scores),
            "adaptive_brier": mean("adaptive_brier"),
            "market_brier": mean("market_brier"),
            "frozen_brier": mean("frozen_brier"),
            "market_minus_adaptive": mean("market_brier")-mean("adaptive_brier"),
            "adaptive_minus_frozen": mean("frozen_brier")-mean("adaptive_brier"),
            "forecast_errors": self.forecast_errors,
            "model_update_days": self.update_days,
            "error_or_loss_update_days": self.loss_day_updates,
            "paper_decisions": len(self.wagers),
            "paper_losses": sum(not x["won"] for x in self.wagers),
            "paper_wins": sum(x["won"] for x in self.wagers),
            "virtual_bankroll_start_ZMW": str(self.policy.starting_bankroll),
            "virtual_bankroll_end_ZMW": str(self.bankroll),
            "virtual_net_ZMW": str(net),
            "virtual_wagered_ZMW": str(wagered),
            "virtual_ROI_percent": str((net/wagered*100).quantize(Decimal("0.01"))) if wagered else None,
            "max_virtual_drawdown_fraction": float(self.max_drawdown),
            "journal_entries": len(self.journal),
            "journal_head_sha256": verify_journal(self.journal),
            "settlement_source_sha256": self.holdout_digest,
            "execution_authority": False,
        }


def _anchored_training(seasons: list[OddsSeason]) -> OddsSeason:
    rows = tuple(sorted((m for season in seasons for m in season.matches),
                        key=lambda m: m.key))
    if len({m.key for m in rows}) != len(rows):
        raise ReplayRefused("training duplicate fixture")
    for previous, current in zip(seasons, seasons[1:]):
        if previous.matches[-1].day >= current.matches[0].day:
            raise ReplayRefused("training seasons overlap or reverse")
    digest = _sha({"season_digests": [s.digest for s in seasons]})
    return OddsSeason(rows, digest, "pinned-anchored-training")


def _fold(train: OddsSeason, holdout: OddsSeason):
    if train.matches[-1].day >= holdout.matches[0].day or train.digest == holdout.digest:
        raise ReplayRefused("holdout chronology or overlap invalid")
    engine = PreliveFeedback(train, holdout.digest)
    # Actual results reside in a different object from the offer interface.
    # Predictions are sealed before the outcome object is constructed.
    for matches in _by_day(holdout.matches):
        offers = tuple(PreMatchOffer(x.day, x.home, x.away, x.prices) for x in matches)
        engine.prepare_day(offers)
        results = tuple(SettledResult(
            x.identity, m.result, m.day+timedelta(days=1), holdout.digest
        ) for x, m in zip(offers, matches))
        engine.settle_day(results)
    return engine


def _cluster_ci(engines: Sequence[PreliveFeedback]) -> tuple[float, float]:
    rng = random.Random(BOOTSTRAP_SEED)
    sets = [engine.day_scores for engine in engines]
    draws = []
    for _ in range(BOOTSTRAP_REPS):
        delta = n = 0
        for days in sets:
            for _ in days:
                x = days[rng.randrange(len(days))]
                delta += x["market_minus_adaptive_sum"]
                n += x["matches"]
        draws.append(delta/n)
    draws.sort()
    return draws[int(0.025*BOOTSTRAP_REPS)], draws[int(0.975*BOOTSTRAP_REPS)]


def retrospective_review(seasons: dict[str, OddsSeason]) -> tuple[dict, list[dict]]:
    if set(seasons) != set(SOURCES):
        raise ReplayRefused("exact four pinned seasons required")
    if any(seasons[name].digest != expected for name, expected in SOURCES.items()):
        raise ReplayRefused("source SHA256 not independently pinned")
    ordered = list(SOURCES)
    if any(seasons[a].matches[-1].day >= seasons[b].matches[0].day
           for a,b in zip(ordered, ordered[1:])):
        raise ReplayRefused("cross-season chronology not admissible")
    all_keys = [m.key for dataset in seasons.values() for m in dataset.matches]
    if len(all_keys) != len(set(all_keys)):
        raise ReplayRefused("duplicate fixture crossing folds")
    engines = []
    for position in range(1,len(ordered)):
        engines.append(_fold(_anchored_training(
            [seasons[name] for name in ordered[:position]]
        ), seasons[ordered[position]]))
    result_folds = []
    total_paper_decisions = 0
    journals = []
    for engine, name in zip(engines, ordered[1:]):
        r = engine.report()
        r["fold"] = name
        r["mode"] = "RETROSPECTIVE_ALREADY_EXAMINED_HISTORICAL_DATA"
        result_folds.append(r)
        total_paper_decisions += r["paper_decisions"]
        journals.append({"fold": name, "entries": engine.journal})
    lo, hi = _cluster_ci(engines)
    all_folds_beat_market = all(
        r["scored_matches"] >= 300 and
        r["market_minus_adaptive"] >= MIN_BRIER_EDGE
        for r in result_folds
    )
    all_folds_paper_positive = all(
        Decimal(r["virtual_net_ZMW"]) > 0 and
        Decimal(str(r["max_virtual_drawdown_fraction"])) <= MAX_DRAWDOWN_FRACTION
        for r in result_folds
    )
    retrospective_pass = (
        all_folds_beat_market and lo > 0 and
        all_folds_paper_positive and total_paper_decisions >= MIN_PAPER_DECISIONS
    )
    report = {
        "schema": SCHEMA,
        "mode": "OFFLINE_PAPER_ONLY_NO_REAL_ACCOUNT",
        "status": "RETROSPECTIVE_PASS_UNTOUCHED_FUTURE_STILL_REQUIRED" if retrospective_pass
                  else "NO_CONSISTENT_RETROSPECTIVE_EDGE_DEMONSTRATED",
        "frozen_predeclared_protocol": "docs/PRELIVE_OUTCOME_LEARNING_PROTOCOL_2026-11-26.md",
        "season_sha256": dict(SOURCES),
        "folds": result_folds,
        "pooled_95pct_day_cluster_bootstrap_market_minus_adaptive": [lo, hi],
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPS,
        "minimum_brier_edge_per_fold": MIN_BRIER_EDGE,
        "minimum_paper_decisions": MIN_PAPER_DECISIONS,
        "max_paper_drawdown_fraction": float(MAX_DRAWDOWN_FRACTION),
        "retrospective_diagnostic_pass": retrospective_pass,
        "settlement_feedback_replayed": all(
            f["model_update_days"] > 0 and f["error_or_loss_update_days"] > 0
            for f in result_folds
        ),
        "requires_separate_focused_test_receipt": True,
        "genuine_unexamined_future_holdout_obtained": False,
        "consistent_predictive_superiority_proven": False,
        "real_account_loss_learning_proven": False,
        "financial_edge_proven": False,
        "live_admission": False,
        "authority": NO_AUTHORITY,
        "independent_settlement_receipts": False,
        "limitations": [
            "Every seasonal fold has already been examined by prior Wolf research.",
            "Historical FTR labels and bookmaker opening quotes originate in the same CSV snapshot.",
            "No live accepted bets, actual settlement receipts or executable market prices.",
            "Retrospective diagnostic cannot replace a genuinely future untouched period.",
            "Learning correctness is not proof that learning improves profitability.",
        ],
        "journal_head_sha256": _sha([r["journal_head_sha256"] for r in result_folds]),
    }
    return report, journals


def verify_retrospective_evidence(report: dict, journals: list[dict]) -> bool:
    """Independent recomputation from a source-bound immutable journal.

    Verifies the public result numerically against pre-outcome predictions
    and later settlement labels, rather than merely trusting report totals.
    It authenticates consistency, NOT the real-world source of a CSV.
    """
    if report.get("schema") != SCHEMA or report.get("authority") != NO_AUTHORITY or (
        report.get("live_admission") is not False or
        report.get("consistent_predictive_superiority_proven") is not False or
        report.get("season_sha256") != SOURCES or
        len(report.get("folds",())) != 3 or len(journals) != 3
    ):
        raise ReplayRefused("inconsistent research schema or authority claims")
    heads = []
    for fold, wrapper in zip(report["folds"], journals):
        if wrapper.get("fold") != fold.get("fold"):
            raise ReplayRefused("fold identity mismatch")
        entries = wrapper.get("entries")
        if not isinstance(entries, list) or len(entries) != 2*fold["scored_days"]:
            raise ReplayRefused("missing prediction or settlement entries")
        head = verify_journal(entries)
        heads.append(head)
        if head != fold["journal_head_sha256"]:
            raise ReplayRefused("fold output contradicts journal head")
        matches = errors = updates = feedback = bets = losses = 0
        scores = {method: 0.0 for method in ("adaptive","market","frozen")}
        previous_day = ""
        previous_model_sha = None
        control_sha = None
        bankroll = Decimal("100")
        peak = bankroll
        maxdd = Decimal(0)
        wagered = Decimal(0)
        for i in range(0,len(entries),2):
            freeze, outcome = entries[i], entries[i+1]
            if (freeze["kind"]!="predictions_frozen_before_outcomes" or
                outcome["kind"]!="settled_then_updated"):
                raise ReplayRefused("prediction/settlement journal ordering invalid")
            first, second = freeze["body"], outcome["body"]
            day = first["date"]
            if day <= previous_day or day != second["date"]:
                raise ReplayRefused("daily journal chronology broken")
            previous_day = day
            if previous_model_sha is not None and first["model_sha256"] != previous_model_sha:
                raise ReplayRefused("model update chain interrupted")
            if control_sha is None:
                control_sha = first["control_sha256"]
            elif control_sha != first["control_sha256"]:
                raise ReplayRefused("frozen control adapted to outcomes")
            if (second["model_sha256_before"] != first["model_sha256"] or
                first["holdout_sha256"] != fold["settlement_source_sha256"] or
                second["receipt_source_sha256"] != fold["settlement_source_sha256"]):
                raise ReplayRefused("forecast model state or historical source changed")
            previous_model_sha = second["model_sha256_after"]
            receipts=second.get("settlement_receipts")
            preds=first["predictions"]
            if not isinstance(receipts,list) or len(receipts)!=len(preds):
                raise ReplayRefused("incomplete independently scored settlements")
            expected_ids={pred["identity"] for pred in preds}
            actual={x["identity"]:x["outcome"] for x in receipts}
            if set(actual)!=expected_ids or len(actual)!=len(receipts):
                raise ReplayRefused("settlement evidence does not match predictions")
            if any(x["source_sha256"]!=fold["settlement_source_sha256"]
                or date.fromisoformat(x["observed_day"])<=date.fromisoformat(day)
                for x in receipts):
                raise ReplayRefused("settlement source or time invalid")
            daily={method:0.0 for method in scores}
            misses=0
            for pred in preds:
                label=actual[pred["identity"]]
                if label not in OUTCOMES:
                    raise ReplayRefused("unknown settled label")
                for method in daily:
                    vals=pred[method]
                    if len(vals)!=3 or any(type(x) is not float or not math.isfinite(x)
                       or x<0 or x>1 for x in vals):
                        raise ReplayRefused("invalid sealed probabilities")
                    daily[method]+=sum(
                        (vals[j]-float(OUTCOMES[j]==label))**2
                        for j in range(3)
                    )
                misses+=int(OUTCOMES[max(range(3),
                       key=lambda j:pred["adaptive"][j])]!=label)
            n=len(preds)
            if second["matches"]!=n or second["prediction_misses"]!=misses:
                raise ReplayRefused("reported labels/forecast errors contradict ledger")
            for method in scores:
                if abs(daily[method]/n-second[method+"_brier"])>1e-9:
                    raise ReplayRefused("reported Brier contradicts sealed probabilities")
                scores[method]+=daily[method]
            if abs((daily["market"]-daily["adaptive"])-
                   second["market_minus_adaptive_sum"])>1e-9:
                raise ReplayRefused("reported market improvement fabricated")
            matches+=n
            errors+=misses
            updates+=int(first["model_sha256"]!=second["model_sha256_after"])
            feedback+=int(
                first["model_sha256"]!=second["model_sha256_after"]
                and (misses>0 or (
                    second["paper"] is not None and not second["paper"]["won"]
                ))
            )
            pick=first["paper_decision"]
            paper=second["paper"]
            if (pick is None) != (paper is None):
                raise ReplayRefused("missing shadow decision outcome")
            if paper is not None:
                if any(paper.get(key)!=value for key,value in pick.items()):
                    raise ReplayRefused("shadow decision changed after settlement")
                outcome_label=actual[pick["identity"]]
                won=pick["selection"]==outcome_label
                if paper["won"] is not won:
                    raise ReplayRefused("shadow decision win/loss attribution incorrect")
                stake=Decimal(pick["stake_virtual_ZMW"])
                if stake > bankroll*Decimal("0.005") or stake<=0:
                    raise ReplayRefused("shadow stake exceeds frozen bound")
                quote=Decimal(pick["quoted_opening_odds"])
                if quote>MAX_QUOTE:
                    raise ReplayRefused("unqualified paper odds")
                gross=stake*(quote-Decimal(1)) if won else -stake
                net=gross-(max(gross,Decimal(0))*Decimal("0.02"))
                bankroll+=net
                wagered+=stake
                peak=max(peak,bankroll)
                maxdd=max(maxdd,(peak-bankroll)/peak)
                if (Decimal(paper["virtual_net_ZMW"])!=net or
                    Decimal(paper["virtual_balance_ZMW"])!=bankroll):
                    raise ReplayRefused("shadow financial ledger inconsistent")
                bets+=1
                losses+=int(not won)
        if (matches!=fold["scored_matches"] or
            errors!=fold["forecast_errors"] or
            updates!=fold["model_update_days"] or
            feedback!=fold["error_or_loss_update_days"] or
            bets!=fold["paper_decisions"] or
            losses!=fold["paper_losses"]):
            raise ReplayRefused("fold totals contradict immutable event history")
        if any(abs(scores[x]/matches-fold[x+"_brier"])>1e-9 for x in scores):
            raise ReplayRefused("fold Brier totals contradict event history")
        if (Decimal(fold["virtual_bankroll_end_ZMW"])!=bankroll or
            Decimal(fold["virtual_net_ZMW"])!=bankroll-Decimal("100") or
            Decimal(fold["virtual_wagered_ZMW"])!=wagered or
            abs(float(maxdd)-fold["max_virtual_drawdown_fraction"])>1e-12):
            raise ReplayRefused("fold paper bankroll or drawdown inconsistent")
    if _sha(heads)!=report["journal_head_sha256"]:
        raise ReplayRefused("pooled journal head mismatch")
    return True


def _write_new(path: Path, body: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor,"wb") as out:
            out.write(body)
            out.flush()
            os.fsync(out.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wolf-Coin settled historical loss feedback; research only")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.private_output_dir.resolve()
    if not output.is_dir() or output.is_symlink() or (
            output.stat().st_mode & 0o077):
        raise ReplayRefused("existing owner-private output directory (mode 0700) required")
    report_file = output/"prelive-feedback.json"
    journal_file = output/"prelive-feedback-journal.json"
    if report_file.exists() or journal_file.exists():
        raise ReplayRefused("refusing to overwrite frozen research output")
    from wolf_lab.odds_replay import load_season
    seasons = {
        name: load_season(args.data_root/("E0-"+name[2:4]+name[5:]+".csv"),
                          expected_sha256=digest)
        for name,digest in SOURCES.items()
    }
    report, journals = retrospective_review(seasons)
    verify_retrospective_evidence(report, journals)
    _write_new(journal_file,_json({"schema":SCHEMA,"journals":journals}))
    _write_new(report_file,_json(report))
    print(json.dumps({
        "status": report["status"], "source_hashes": report["season_sha256"],
        "report_sha256": sha256(report_file.read_bytes()).hexdigest(),
        "journal_sha256": sha256(journal_file.read_bytes()).hexdigest(),
        "learning_feedback_tests": "RUN_SEPARATELY",
        "genuine_superiority": report["consistent_predictive_superiority_proven"],
        "live_admission": False,
    },sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ReplayRefused, OSError, ValueError) as error:
        print(json.dumps({"status":"REFUSED","error":str(error),"live_admission":False}),
              file=sys.stderr)
        sys.exit(2)
