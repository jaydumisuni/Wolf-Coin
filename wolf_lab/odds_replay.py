"""Deterministic 1X2 football historical replay, strictly research-only.

Historical bookmaker odds are *quoted prices*, not verified executable orders.
Train 2023/24 and holdout 2024/25 are strictly disjoint. The model and policy
are fixed before holdout; results are never used to adjust picks on match day.
No network, wallet, bookmaker endpoint, or live-effect capability exists here.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN, localcontext
import csv
from hashlib import sha256
import json
from math import log, pow
from pathlib import Path
from typing import Iterable, Sequence

from wolf_core.contracts import ContractError, money

OUTCOMES = ("H", "D", "A")
PROVENANCE = "football-data.co.uk historical league CSV (research-only)"
DATA_LIMIT_BYTES = 1_000_000
NUM = Decimal("0.01")


class ReplayRefused(ContractError):
    pass


@dataclass(frozen=True)
class OddsMatch:
    day: date
    home: str
    away: str
    result: str
    prices: tuple[Decimal, Decimal, Decimal]

    def __post_init__(self):
        if not self.home or not self.away or self.home == self.away:
            raise ReplayRefused("invalid match teams")
        if self.result not in OUTCOMES:
            raise ReplayRefused("invalid three-way final result")
        if len(self.prices) != 3 or any(
                not isinstance(x, Decimal) or not x.is_finite() or x <= Decimal("1") or x > Decimal("1000")
                for x in self.prices):
            raise ReplayRefused("invalid bookmaker quote")

    @property
    def key(self):
        return self.day.isoformat(), self.home, self.away


@dataclass(frozen=True)
class OddsSeason:
    matches: tuple[OddsMatch, ...]
    digest: str
    path: str


@dataclass(frozen=True)
class ReplayPolicy:
    starting_bankroll: Decimal = Decimal("100")
    max_daily_stake_fraction: Decimal = Decimal("0.005")
    min_expected_value: Decimal = Decimal("0.05")
    stake_increment: Decimal = Decimal("0.01")
    hypothetical_win_commission: Decimal = Decimal("0.02")
    home_elo_bonus: float = 65.0
    elo_step: float = 20.0
    draw_probability_min: float = 0.15
    draw_probability_max: float = 0.35

    def __post_init__(self):
        for key in ("starting_bankroll", "max_daily_stake_fraction", "min_expected_value",
                    "stake_increment", "hypothetical_win_commission"):
            value = money(getattr(self, key), nonnegative=True)
            object.__setattr__(self, key, value)
        if (self.starting_bankroll <= 0 or self.max_daily_stake_fraction <= 0
                or self.max_daily_stake_fraction > Decimal("0.005")
                or self.stake_increment <= 0 or self.min_expected_value > Decimal("0.5")
                or self.hypothetical_win_commission > Decimal("0.2")):
            raise ReplayRefused("research configuration outside hard bounds")
        for key in ("home_elo_bonus", "elo_step", "draw_probability_min", "draw_probability_max"):
            v = getattr(self, key)
            if type(v) is not float or not (0 < v < 500):
                raise ReplayRefused("invalid fixed research parameter")
        if not (0 < self.draw_probability_min <= self.draw_probability_max < 1):
            raise ReplayRefused("invalid draw bounds")


def load_season(path: Path | str, *, expected_sha256: str) -> OddsSeason:
    path = Path(path).resolve()
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ReplayRefused("expected independent SHA256 digest required")
    raw = path.read_bytes()
    if not 0 < len(raw) < DATA_LIMIT_BYTES:
        raise ReplayRefused("historical CSV exceeds bounded read")
    digest = sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ReplayRefused("historical CSV digest does not match frozen evidence")
    try:
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    except (UnicodeError, csv.Error) as exc:
        raise ReplayRefused("malformed odds CSV") from exc
    if len(rows) < 50 or len(rows) > 10_000:
        raise ReplayRefused("historical season sample too small or oversized")
    matches: list[OddsMatch] = []
    observed = set()
    for row in rows:
        try:
            day = datetime.strptime(row["Date"], "%d/%m/%Y").date()
            home, away = row["HomeTeam"].strip(), row["AwayTeam"].strip()
            result = row["FTR"].strip().upper()
            prices = tuple(Decimal(row[key]) for key in ("B365H", "B365D", "B365A"))
        except (KeyError, AttributeError, ValueError, TypeError, ArithmeticError) as exc:
            raise ReplayRefused("missing or malformed date, result or quoted price") from exc
        m = OddsMatch(day, home, away, result, prices)
        if m.key in observed:
            raise ReplayRefused("duplicate match identity")
        observed.add(m.key)
        matches.append(m)
    return OddsSeason(tuple(sorted(matches, key=lambda m: m.key)), digest, str(path))


@dataclass
class EloResearchModel:
    home_bonus: float
    step: float
    draw_probability: float
    ratings: dict[str, float] = field(default_factory=dict)

    def prediction(self, m: OddsMatch) -> dict[str, float]:
        home = self.ratings.get(m.home, 1500.0)
        away = self.ratings.get(m.away, 1500.0)
        home_conditional = 1.0 / (1.0 + pow(10.0, ((away - home - self.home_bonus) / 400.0)))
        pdraw = self.draw_probability
        return {"H": (1-pdraw)*home_conditional, "D": pdraw,
                "A": (1-pdraw)*(1-home_conditional)}

    def learn_after_day(self, day_matches: Sequence[OddsMatch]) -> None:
        # All same-day ratings are updated together using yesterday's ratings,
        # not by allowing one match's result to inform another of the same day.
        old = dict(self.ratings)
        changes: dict[str, float] = defaultdict(float)
        for m in day_matches:
            rh = old.get(m.home, 1500.0)
            ra = old.get(m.away, 1500.0)
            expected = 1 / (1 + pow(10.0, ((ra - rh - self.home_bonus) / 400.0)))
            outcome = 1.0 if m.result == "H" else 0.0 if m.result == "A" else 0.5
            adjustment = self.step * (outcome - expected)
            changes[m.home] += adjustment
            changes[m.away] -= adjustment
        for team, diff in changes.items():
            self.ratings[team] = old.get(team,1500.0) + diff


def _by_day(matches: Iterable[OddsMatch]):
    current = None
    group: list[OddsMatch] = []
    for match in matches:
        if current is not None and match.day != current:
            yield group
            group = []
        group.append(match)
        current = match.day
    if group:
        yield group


def _proper_score(probabilities: dict[str, float], outcome: str):
    # 1X2 Brier score, lower is better.
    return sum((probabilities[o] - float(o == outcome)) ** 2 for o in OUTCOMES)


def _no_vig(m: OddsMatch):
    implied = {o: float(1/m.prices[i]) for i, o in enumerate(OUTCOMES)}
    overround = sum(implied.values())
    return {o: implied[o] / overround for o in OUTCOMES}


def _rounded_stake(bankroll: Decimal, policy: ReplayPolicy):
    limit = bankroll * policy.max_daily_stake_fraction
    steps = (limit / policy.stake_increment).to_integral_value(rounding=ROUND_DOWN)
    return steps * policy.stake_increment


def _train(train: OddsSeason, policy: ReplayPolicy) -> EloResearchModel:
    draw_rate = sum(m.result == "D" for m in train.matches) / len(train.matches)
    bounded = max(policy.draw_probability_min, min(policy.draw_probability_max, draw_rate))
    model = EloResearchModel(policy.home_elo_bonus, policy.elo_step, bounded)
    for day_matches in _by_day(train.matches):
        model.learn_after_day(day_matches)
    return model


def replay(train: OddsSeason, holdout: OddsSeason, *, policy: ReplayPolicy = ReplayPolicy()) -> dict:
    if train.digest == holdout.digest:
        raise ReplayRefused("train and holdout cannot be the same dataset")
    if train.matches[-1].day >= holdout.matches[0].day:
        raise ReplayRefused("out-of-sample data must follow training chronologically")
    train_keys = {m.key for m in train.matches}
    if any(m.key in train_keys for m in holdout.matches):
        raise ReplayRefused("match identity leaked between training and holdout")
    model = _train(train, policy)
    bankroll = policy.starting_bankroll
    highest_bankroll = bankroll
    biggest_drawdown = Decimal("0")
    wagered = Decimal("0")
    profit = Decimal("0")
    bets = 0
    wins = 0
    no_bet_days = 0
    model_score = 0.0
    market_score = 0.0
    days = 0
    ledger: list[dict] = []
    for day_matches in _by_day(holdout.matches):
        days += 1
        opportunities = []
        for m in day_matches:
            predicted = model.prediction(m)
            model_score += _proper_score(predicted, m.result)
            market_score += _proper_score(_no_vig(m), m.result)
            for i, outcome in enumerate(OUTCOMES):
                # EV uses only forecast and pre-match quoted price, never
                # the result; the result is consulted after selection.
                ev = Decimal(str(predicted[outcome])) * m.prices[i] - Decimal("1")
                if ev >= policy.min_expected_value:
                    opportunities.append((ev, m.key, outcome, m.prices[i], m.result))
        opportunities.sort(key=lambda x: (-x[0], x[1], x[2]))
        stake = _rounded_stake(bankroll, policy)
        if not opportunities or stake <= 0:
            no_bet_days += 1
        else:
            ev, identity, selection, price, result = opportunities[0]
            won = selection == result
            gross = stake*(price - Decimal("1")) if won else -stake
            commission = max(gross, Decimal("0")) * policy.hypothetical_win_commission
            net = gross - commission
            bankroll += net
            wagered += stake
            profit += net
            bets += 1
            wins += int(won)
            highest_bankroll = max(highest_bankroll, bankroll)
            biggest_drawdown = max(biggest_drawdown, (highest_bankroll - bankroll) / highest_bankroll)
            ledger.append({
                "day": identity[0], "fixture": f"{identity[1]} vs {identity[2]}",
                "pick": selection, "actual": result, "odds": str(price),
                "estimated_ev": str(ev.quantize(Decimal("0.0001"))),
                "stake": str(stake), "net": str(net.quantize(Decimal("0.000001"))),
                "balance": str(bankroll.quantize(Decimal("0.000001"))),
                "won": won,
            })
        model.learn_after_day(day_matches)
    n = len(holdout.matches)
    return {
        "schema":"wolf.historical-odds-replay.v1",
        "mode":"HISTORICAL_RESEARCH_PAPER_ONLY",
        "provider":"historical quoted Bet365 opening odds from football-data.co.uk",
        "data_source": PROVENANCE,
        "train_sha256":train.digest, "holdout_sha256":holdout.digest,
        "train_matches":len(train.matches), "holdout_matches":n,
        "train_end":train.matches[-1].day.isoformat(),
        "holdout_start":holdout.matches[0].day.isoformat(),
        "holdout_end":holdout.matches[-1].day.isoformat(),
        "strategy":"fixed ELO team ratings + frozen draw prior + single highest-EV pick per calendar day",
        "fixed_parameters":{"home_elo_bonus":policy.home_elo_bonus,"elo_step":policy.elo_step,
                            "min_ev":str(policy.min_expected_value),"max_daily_fraction":str(policy.max_daily_stake_fraction),
                            "win_commission":str(policy.hypothetical_win_commission)},
        "starting_virtual_ZMW":str(policy.starting_bankroll),
        "ending_virtual_ZMW":str(bankroll.quantize(Decimal("0.000001"))),
        "net_virtual_ZMW":str(profit.quantize(Decimal("0.000001"))),
        "wagered_virtual_ZMW":str(wagered),
        "bets":bets, "wins":wins, "holdout_days":days, "abstained_days":no_bet_days,
        "roi_on_wagers_percent":str((profit/wagered*100).quantize(Decimal("0.01"))) if wagered else None,
        "return_on_start_percent":str((profit/policy.starting_bankroll*100).quantize(Decimal("0.01"))),
        "maximum_peak_drawdown_percent":str((biggest_drawdown*100).quantize(Decimal("0.01"))),
        "model_brier":round(model_score/n,6),"market_no_vig_brier":round(market_score/n,6),
        "model_beats_market_on_brier": model_score < market_score,
        "ledger":ledger,
        "live_ready":False, "profit_proven":False,
        "restrictions": [
            "Historical opening odds do not prove prices executable in Zambia or available at time of prediction.",
            "Team ELO constants were fixed without independent calibration; one holdout season is not proof of future edge.",
            "Missing operator minimum stake, taxes, settlement adjustments, limits and real slippage; paper-only.",
            "No betting or brokerage execution adapter, API credentials, live funds or account access."
        ],
    }


def render_html(report: dict) -> str:
    """Static HTML research report; no scripts, external data, or event actions."""
    from html import escape
    def e(x): return escape(str(x), quote=True)
    rows = "".join(
        "<tr>" + "".join("<td>"+e(row[k])+"</td>" for k in
                         ("day","fixture","pick","actual","odds","stake","net","balance"))+"</tr>"
        for row in report["ledger"]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Wolf-Coin | Historical Replay</title>
<style>body{{background:#101827;color:#e9f2ff;font:15px system-ui;margin:auto;max-width:1120px;padding:28px}}
h1{{color:#91edff}}.panel{{background:#19243a;padding:20px;border-radius:14px;margin:14px 0}}
b{{color:#fff}}.muted{{color:#aec0d8}}table{{width:100%;border-collapse:collapse;display:block;overflow-x:auto}}
td,th{{padding:10px;border-bottom:1px solid #334661;text-align:left;white-space:nowrap}}
.warn{{color:#ffcc91}}.val{{font-size:25px;font-weight:700}}
</style></head><body><h1>Wolf-Coin / Historical research</h1>
<p class="warn">PAPER ONLY · Historical results are not evidence of live profitability or fund readiness.</p>
<section class="panel"><h2>Untouched holdout replay</h2>
<p>Training: {e(report["train_matches"])} fixtures · Holdout: {e(report["holdout_matches"])} fixtures</p>
<p>Virtual starting K{e(report["starting_virtual_ZMW"])} · Ending <span class="val">K{e(report["ending_virtual_ZMW"])}</span> · Net K{e(report["net_virtual_ZMW"])}</p>
<p>{e(report["bets"])} paper selections · ROI on staked funds {e(report["roi_on_wagers_percent"])}% · Maximum drawdown {e(report["maximum_peak_drawdown_percent"])}%</p></section>
<section class="panel"><h2>Calibration against the market</h2>
<p>Wolf ELO Brier: {e(report["model_brier"])} · Market no-vig Brier: {e(report["market_no_vig_brier"])} (lower is better)</p>
<p class="muted">These figures are from real historical match results, not real Wolf-Coin bets.</p></section>
<section class="panel"><h2>Chronological paper ledger</h2><table><thead>
<tr><th>Date</th><th>Fixture</th><th>Pick</th><th>Result</th><th>Odds</th><th>Stake (K)</th><th>Net (K)</th><th>Bankroll (K)</th></tr>
</thead><tbody>{rows}</tbody></table></section>
<p class="muted">Evidence: train SHA-256 {e(report["train_sha256"])}; holdout SHA-256 {e(report["holdout_sha256"])}.</p>
</body></html>"""
