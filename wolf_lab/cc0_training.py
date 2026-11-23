"""CC0-only, source-pinned Premier League training material.

Historical results from openfootball/football.json are licensed CC0-1.0,
not sourced from Football-Data historical odds. No bookmaker prices,
post-match information or venue credentials enter the model.
A game is featurized only with statistics available before its UTC DATE,
then all same-day results are applied after all same-day features are made.
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Sequence
import json
import math

SOURCE_REPO = "https://github.com/openfootball/football.json"
SOURCE_REV = "e6744429ee395bc86f247348c6184bb08d4eb361"
CC0 = "CC0-1.0"
FEATURES = (
    "home_prior_points", "away_prior_points",
    "home_attack", "away_attack", "home_defense", "away_defense",
    "home_recent_points", "away_recent_points", "prior_games_diff",
    "home_advantage",
)


class CC0SourceError(ValueError): pass


@dataclass(frozen=True)
class Fixture:
    day: date
    home: str
    away: str
    home_goals: int | None
    away_goals: int | None
    season: str
    @property
    def outcome(self):
        if self.home_goals is None or self.away_goals is None: return None
        return 0 if self.home_goals > self.away_goals else 2 if self.home_goals < self.away_goals else 1
    @property
    def key(self):
        return (self.day.isoformat(),self.home,self.away)


@dataclass(frozen=True)
class SeasonSource:
    season: str
    digest: str
    fixtures: tuple[Fixture,...]
    scored: int
    unscored: int


def _team(name: str) -> str:
    if not isinstance(name,str) or not 1<=len(name.strip())<=90:
        raise CC0SourceError("invalid team identity")
    val=" ".join(name.casefold().split())
    if val.endswith(" fc"): val=val[:-3]
    if val.startswith("afc "): val=val[4:]
    aliases={"man utd":"manchester united","man city":"manchester city",
             "wolves":"wolverhampton wanderers","spurs":"tottenham hotspur",
             "west ham":"west ham united","nott'm forest":"nottingham forest"}
    return aliases.get(val,val)


def load_cc0(path: Path, *, season: str, sha256_expected: str,
             allow_missing: bool=False) -> SeasonSource:
    if not isinstance(sha256_expected,str) or len(sha256_expected)!=64:
        raise CC0SourceError("source SHA256 required")
    blob=Path(path).read_bytes()
    if not 100 < len(blob) <= 2_000_000:
        raise CC0SourceError("source JSON size outside bounded range")
    digest=sha256(blob).hexdigest()
    if digest!=sha256_expected:
        raise CC0SourceError("source revision content hash mismatch")
    try: src=json.loads(blob)
    except (UnicodeError,ValueError) as e: raise CC0SourceError("not valid source JSON") from e
    if not isinstance(src,dict) or not isinstance(src.get("matches"),list):
        raise CC0SourceError("unexpected CC0 match format")
    if not 75<=len(src["matches"])<=600:
        raise CC0SourceError("season expected count outside bounds")
    seen=set(); fixtures=[]; missing=0
    for row in src["matches"]:
        try:
            dt=date.fromisoformat(row["date"])
            if not row["date"].startswith(season[:4]+"-") and not row["date"].startswith(str(int(season[:4])+1)+"-"):
                raise CC0SourceError("match date outside season bounds")
            h,a=_team(row["team1"]),_team(row["team2"])
            if h==a: raise CC0SourceError("self-match")
            score=row.get("score",{})
            ft=score.get("ft") if isinstance(score,dict) else None
            if isinstance(ft,list) and len(ft)==2 and all(type(x)==int and 0<=x<=20 for x in ft):
                hg,ag=ft
            elif ft is None or ft==[]:
                hg=ag=None;missing+=1
            else: raise CC0SourceError("malformed full-time score")
            fixture=Fixture(dt,h,a,hg,ag,season)
            if fixture.key in seen: raise CC0SourceError("duplicate fixture")
            seen.add(fixture.key)
            fixtures.append(fixture)
        except CC0SourceError:
            raise
        except (TypeError,KeyError,ValueError,AttributeError) as e:
            raise CC0SourceError("malformed fixture schema or timestamp") from e
    if missing and not allow_missing:
        raise CC0SourceError(f"incomplete season: {missing} unscored fixtures")
    return SeasonSource(season,digest,tuple(sorted(fixtures,key=lambda f:f.key)),len(fixtures)-missing,missing)


@dataclass
class _Stats:
    n:int=0
    points:float=0
    gf:float=0
    ga:float=0
    recent:deque[int]=field(default_factory=lambda:deque(maxlen=6))
    def apply(self, gf:int,ga:int):
        self.n+=1;self.gf+=gf;self.ga+=ga
        p=3 if gf>ga else 1 if gf==ga else 0
        self.points+=p;self.recent.append(p)


@dataclass(frozen=True)
class Example:
    key:tuple[str,str,str]
    season:str
    features:tuple[float,...]
    label:int | None


def _features(home:_Stats, away:_Stats)->tuple[float,...]:
    def pts(s):return (s.points+6*1.35)/(s.n+6)/3
    def attack(s):return (s.gf+6*1.35)/(s.n+6)/3
    def defense(s):return (s.ga+6*1.35)/(s.n+6)/3
    def form(s):return (sum(s.recent)+5*1.35)/(len(s.recent)+5)/3
    return (
        pts(home),pts(away),attack(home),attack(away),
        defense(home),defense(away),form(home),form(away),
        (min(home.n,40)-min(away.n,40))/40,1.0
    )


def featurize(seasons: Sequence[SeasonSource]) -> tuple[tuple[Example,...],...]:
    if not seasons:raise CC0SourceError("no season partitions")
    all_seen=set();state:dict[str,_Stats]=defaultdict(_Stats)
    results=[];previous_last:date|None=None
    for source in seasons:
        if not source.fixtures: raise CC0SourceError("empty season")
        if previous_last is not None and source.fixtures[0].day<=previous_last:
            raise CC0SourceError("source seasons reversed or overlapping")
        previous_last=source.fixtures[-1].day
        dates:dict[date,list[Fixture]]=defaultdict(list)
        for m in source.fixtures:
            if m.key in all_seen:raise CC0SourceError("duplicate across seasons")
            all_seen.add(m.key);dates[m.day].append(m)
        rows=[]
        for day,matches in sorted(dates.items()):
            for m in matches:
                rows.append(Example(m.key,m.season,_features(state[m.home],state[m.away]),m.outcome))
            for m in matches:
                if m.outcome is not None:
                    state[m.home].apply(m.home_goals,m.away_goals)
                    state[m.away].apply(m.away_goals,m.home_goals)
        results.append(tuple(rows))
    return tuple(results)
