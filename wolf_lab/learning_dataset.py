"""Leakage-resistant, source-hash-bound pre-match football features.

Materializes a private research candidate, not SUP-qualified truth. Every
feature uses prior match days only; results and goals update team history only
AFTER all matches scheduled on the same date have received their features.
Historic bookmaker opening odds have NO independently verified quote timestamp.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import csv

from wolf_lab.odds_replay import ReplayRefused, OUTCOMES, DATA_LIMIT_BYTES

SOURCE = "football-data.co.uk/E0/historical-research-private"
FEATURE_NAMES = (
    "bias", "shrunk_points_delta", "shrunk_attack_delta",
    "shrunk_defense_delta", "shrunk_form_delta", "experience_delta",
)


@dataclass(frozen=True)
class MatchInput:
    day: date
    home: str
    away: str
    home_goals: int
    away_goals: int
    outcome: str
    odds: tuple[float, float, float]
    season: str

    @property
    def key(self):
        return (self.day.isoformat(), self.home, self.away)


@dataclass(frozen=True)
class FeatureRow:
    day: str
    season: str
    match_id: str
    features: tuple[float, ...]
    market: tuple[float, float, float]
    label: int
    prices: tuple[float, float, float]
    home_prior_games: int
    away_prior_games: int


@dataclass
class TeamHistory:
    n: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    recent: deque[int] = field(default_factory=lambda: deque(maxlen=5))

    def record(self, scored: int, conceded: int):
        self.n += 1
        self.goals_for += scored
        self.goals_against += conceded
        p = 3 if scored > conceded else 1 if scored == conceded else 0
        self.points += p
        self.recent.append(p)


def _features(h: TeamHistory, a: TeamHistory) -> tuple[float, ...]:
    # Explicit fixed shrinkage; never estimated using future rows.
    def points(t: TeamHistory):
        return (t.points + 5 * 1.30) / (t.n + 5)
    def scored(t: TeamHistory):
        return (t.goals_for + 5 * 1.40) / (t.n + 5)
    def conceded(t: TeamHistory):
        return (t.goals_against + 5 * 1.40) / (t.n + 5)
    def form(t: TeamHistory):
        return (sum(t.recent) + 5 * 1.30) / (len(t.recent) + 5)
    return (
        1.0,
        (points(h) - points(a)) / 3.0,
        (scored(h) - scored(a)) / 3.0,
        (conceded(a) - conceded(h)) / 3.0,
        (form(h) - form(a)) / 3.0,
        (min(h.n, 30) - min(a.n, 30)) / 30.0,
    )


def load_verified(path: Path, *, expected_sha256: str, season: str) -> list[MatchInput]:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ReplayRefused("independent expected season SHA-256 is required")
    file = Path(path).resolve()
    content = file.read_bytes()
    if not 0 < len(content) < DATA_LIMIT_BYTES:
        raise ReplayRefused("season file outside size bounds")
    if sha256(content).hexdigest() != expected_sha256:
        raise ReplayRefused("season source digest mismatch")
    try:
        lines = csv.DictReader(content.decode("utf-8-sig").splitlines())
        raw = list(lines)
    except (csv.Error, UnicodeError) as exc:
        raise ReplayRefused("invalid fixture CSV") from exc
    if not 50 <= len(raw) <= 500:
        raise ReplayRefused("fixture sample outside historical bounds")
    seen: set[tuple] = set()
    result = []
    for row in raw:
        try:
            day = datetime.strptime(row["Date"], "%d/%m/%Y").date()
            h, a = row["HomeTeam"].strip(), row["AwayTeam"].strip()
            home_goals = int(row["FTHG"])
            away_goals = int(row["FTAG"])
            outcome = row["FTR"].strip()
            prices = tuple(float(Decimal(row[k])) for k in ("B365H","B365D","B365A"))
            if not h or not a or h == a or not 0 <= home_goals <= 20 or not 0 <= away_goals <= 20:
                raise ValueError("invalid match")
            if outcome not in OUTCOMES or outcome != (
                "H" if home_goals > away_goals else "A" if away_goals > home_goals else "D"
            ):
                raise ValueError("score/label conflict")
            if any(not 1.0 < x <= 1000.0 for x in prices):
                raise ValueError("invalid odds")
            if (day,h,a) in seen:
                raise ValueError("duplicate fixture")
            seen.add((day,h,a))
            result.append(MatchInput(day,h,a,home_goals,away_goals,outcome,prices,season))
        except (ValueError, KeyError, TypeError, AttributeError, ArithmeticError) as exc:
            raise ReplayRefused("unqualified historical fixture or score") from exc
    return sorted(result,key=lambda x:x.key)


def materialize(partitions: tuple[list[MatchInput],...]) -> tuple[tuple[FeatureRow,...],...]:
    if not partitions or any(not p for p in partitions):
        raise ReplayRefused("all materialization periods must contain matches")
    for left, right in zip(partitions, partitions[1:]):
        if max(x.day for x in left) >= min(x.day for x in right):
            raise ReplayRefused("materialization periods overlap or reverse")
    result: list[tuple[FeatureRow,...]] = []
    seen: set[tuple] = set()
    history: dict[str,TeamHistory] = defaultdict(TeamHistory)
    for matches in partitions:
        output = []
        by_date: dict[date,list[MatchInput]] = defaultdict(list)
        for m in matches:
            if m.key in seen:
                raise ReplayRefused("repeated fixture across partitions")
            seen.add(m.key)
            by_date[m.day].append(m)
        for day, fixtures in sorted(by_date.items()):
            for m in sorted(fixtures,key=lambda x:x.key):
                h, a = history[m.home],history[m.away]
                inverse = tuple(1/x for x in m.odds)
                overround = sum(inverse)
                market = tuple(x/overround for x in inverse)
                output.append(FeatureRow(
                    day=m.day.isoformat(),season=m.season,
                    match_id=f"{m.day.isoformat()}|{m.home}|{m.away}",
                    features=_features(h,a),market=market,
                    label=OUTCOMES.index(m.outcome),prices=m.odds,
                    home_prior_games=h.n,away_prior_games=a.n))
            # Strict same-day boundary: labels used here only after every
            # fixture for this calendar date was featurized.
            for m in fixtures:
                history[m.home].record(m.home_goals,m.away_goals)
                history[m.away].record(m.away_goals,m.home_goals)
        result.append(tuple(output))
    return tuple(result)
