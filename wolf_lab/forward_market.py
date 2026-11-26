"""Pre-match quote evidence intake for Wolf-Coin's already frozen 270 fixtures.

A locally hashed quote is NOT an independently authenticated bookmaker
price, and never authorizes financial activity. The data is separate from
forecast generation and model training. Schedule corrections are additive,
preserving the exact original fixture identity.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit
import json
import os
import re

SCHEMA="wolf.forward-market-capture.v1"
FREEZE_SCHEMA="wolf.prelive-forward-freeze.v1"
SOURCE_SHA="53944d9ed2869dd0114a29859df1196c525c7229f4cdac8d3c55f5b92819bec9"
FORECAST_DIGEST="decefdda4ceb1d345d620e9f88a2007498e8d40e0b076ca04dac20df3e942a88"
MAX_EVIDENCE_BYTES=1024*1024
QUOTE_CLASSES=("HOME","DRAW","AWAY")


class QuoteRefused(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _utc(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise QuoteRefused("UTC Z timestamp required")
    try:
        t=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as e:
        raise QuoteRefused("invalid UTC timestamp") from e
    if t.utcoffset().total_seconds()!=0:
        raise QuoteRefused("non-UTC timestamp refused")
    return t


def _identity(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9:_|. &\-]{4,260}",value):
        raise QuoteRefused("invalid identity")
    return value


def _url(value):
    if not isinstance(value,str):
        raise QuoteRefused("evidence URL required")
    try:
        p=urlsplit(value)
    except ValueError as e:
        raise QuoteRefused("invalid evidence URL") from e
    if p.scheme!="https" or not p.hostname or p.username or p.password or p.fragment:
        raise QuoteRefused("public HTTPS evidence URL required")
    if p.hostname in ("localhost","127.0.0.1","0.0.0.0") or not re.fullmatch(r"[a-zA-Z0-9.\-]{3,180}",p.hostname):
        raise QuoteRefused("invalid public source")
    return value


def _prices(value):
    if not isinstance(value,(list,tuple)) or len(value)!=3 or any(type(v) not in (float,int) or not isfinite(v) or v<=1.0 or v>=1000.0 for v in value):
        raise QuoteRefused("three finite market 1X2 decimal prices required")
    return tuple(float(x) for x in value)


@dataclass(frozen=True)
class MarketQuote:
    capture_id: str
    fixture_identity: str
    quoted_fixture_day: str
    kickoff_utc: str
    observed_utc: str
    provider: str
    source_url: str
    decimal_odds_1x2: tuple[float,float,float]
    evidence_sha256: str
    evidence_kind: str="provider_snapshot_json"
    schedule_source_url: str|None=None
    schedule_evidence_sha256: str|None=None
    transport_evidence_sha256: str|None=None

    def __post_init__(self):
        _identity(self.capture_id)
        _identity(self.fixture_identity)
        if not isinstance(self.provider,str) or not re.fullmatch(r"[A-Za-z0-9 .\-_]{3,100}",self.provider):
            raise QuoteRefused("provider identity invalid")
        if self.evidence_kind not in ("provider_snapshot_json","public_1x2_html"):
            raise QuoteRefused("unrecognized evidence structure")
        _url(self.source_url)
        if not isinstance(self.quoted_fixture_day,str):
            raise QuoteRefused("fixture day required")
        try:
            date.fromisoformat(self.quoted_fixture_day)
        except ValueError as e:
            raise QuoteRefused("invalid fixture day") from e
        observed=_utc(self.observed_utc)
        kickoff=_utc(self.kickoff_utc)
        if kickoff.date()!=date.fromisoformat(self.quoted_fixture_day):
            raise QuoteRefused("quoted date and UTC kickoff disagree")
        if observed>=kickoff:
            raise QuoteRefused("post-kickoff quote refused")
        if observed>datetime.now(timezone.utc):
            raise QuoteRefused("future-dated quote refused")
        object.__setattr__(self,"decimal_odds_1x2",_prices(self.decimal_odds_1x2))
        if not isinstance(self.evidence_sha256,str) or not re.fullmatch("[0-9a-f]{64}",self.evidence_sha256):
            raise QuoteRefused("quote evidence SHA-256 required")
        if self.schedule_source_url is not None:
            _url(self.schedule_source_url)
        if self.schedule_evidence_sha256 is not None and not re.fullmatch("[0-9a-f]{64}",self.schedule_evidence_sha256):
            raise QuoteRefused("invalid schedule evidence SHA-256")
        if self.transport_evidence_sha256 is not None and not re.fullmatch("[0-9a-f]{64}",self.transport_evidence_sha256):
            raise QuoteRefused("invalid transport header SHA-256")


def frozen(path:Path)->dict:
    body=path.read_bytes()
    if sha256(body).hexdigest()!=SOURCE_SHA:
        raise QuoteRefused("original prospective forecast bytes changed")
    x=json.loads(body)
    original=dict(x)
    claimed=original.pop("forecast_digest_sha256",None)
    if claimed!=FORECAST_DIGEST or digest(original)!=claimed:
        raise QuoteRefused("original prospective forecast seal mismatch")
    if (x.get("schema")!=FREEZE_SCHEMA or x.get("cutoff_date")!="2026-11-26"
        or x.get("future_match_count")!=270 or x.get("live_admission") is not False
        or x.get("financial_edge_proven") is not False or x.get("market_odds_available") is not False):
        raise QuoteRefused("unqualified source forecast universe")
    records=x.get("records")
    if not isinstance(records,list) or len(records)!=270:
        raise QuoteRefused("incorrect source fixture universe")
    ids={r["identity"]:r for r in records}
    if len(ids)!=270 or any(r["identity"].split("|")[0]!=r["fixture_day"] for r in records):
        raise QuoteRefused("non-unique or mismatched forecast fixture")
    return x


def _quote_dict(item:MarketQuote):
    data=json.loads(canonical(asdict(item)))
    # Preserve original pre-transport journals without altering their digest.
    if data.get("transport_evidence_sha256") is None:
        data.pop("transport_evidence_sha256",None)
    return data


def _transport_proof(raw:bytes,item:MarketQuote):
    from email.utils import parsedate_to_datetime
    if item.transport_evidence_sha256 is None:
        raise QuoteRefused("transport evidence required for this capture")
    if not isinstance(raw,bytes) or sha256(raw).hexdigest()!=item.transport_evidence_sha256:
        raise QuoteRefused("transport header SHA-256 mismatch")
    try:
        lines=raw.decode("utf-8").splitlines()
        entries=[]
        for index,line in enumerate(lines):
            if line.startswith("HTTP/"):
                entries.append((index,line.strip()))
        if not entries or not entries[-1][1].endswith(" 200") and " 200 " not in entries[-1][1]:
            raise QuoteRefused("no successful HTTP source readback")
        headers=lines[entries[-1][0]+1:]
        dates=[x[5:].strip() for x in headers if x.lower().startswith("date:")]
        if len(dates)!=1:
            raise QuoteRefused("HTTP source Date not unique")
        timestamp=parsedate_to_datetime(dates[0]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if timestamp!=item.observed_utc:
            raise QuoteRefused("observed timestamp contradicts HTTP Date")
    except QuoteRefused:
        raise
    except (ValueError,TypeError,UnicodeError) as e:
        raise QuoteRefused("invalid HTTP transport evidence") from e
    return True


def _html_quoted_evidence(raw:bytes,item:MarketQuote):
    """Parse one pinned TipsterArea public source page, no DOM actions or wagers.

    Matching of provider, teams, date and three odds is mandatory.
    Arbitrary HTML, schedule-only pages and other markets are rejected.
    """
    from html import unescape
    if not item.source_url.startswith("https://tipsterarea.com/match/"):
        raise QuoteRefused("unrecognized public HTML quote publisher")
    try:
        html=raw.decode("utf-8")
    except UnicodeError as e:
        raise QuoteRefused("invalid public quote HTML encoding") from e
    kickoff=re.search(r'<div\s+id="time"[^>]*content="([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2})"',html)
    if not kickoff or (kickoff.group(1)+":00Z")!=item.kickoff_utc:
        raise QuoteRefused("public page kickoff does not match quote")
    teams=re.findall(r'<h2\s+itemprop="name">([^<]+)</h2>',html)
    if len(teams)!=2:
        raise QuoteRefused("public source team identity not unique")
    names=tuple(re.sub(r"\s+"," ",unescape(x).strip().lower()) for x in teams)
    parts=item.fixture_identity.split("|")
    if len(parts)!=3 or names!=(parts[1],parts[2]):
        raise QuoteRefused("public page teams do not match frozen fixture")
    market=re.search(r'<th class="odds-type">Standard 1X2</th>(.*?)</table>',html,re.S)
    if not market:
        raise QuoteRefused("standard 1X2 quotes absent from page")
    book=item.provider.removeprefix("TipsterArea ")
    odds=re.findall(r'<tr>\s*<td class="bookmaker">\s*<img[^>]+alt="([^"]+)"[^>]*/>\s*</td>\s*<td class="odd">([0-9]+(?:\.[0-9]+)?)</td>\s*<td class="odd">([0-9]+(?:\.[0-9]+)?)</td>\s*<td class="odd">([0-9]+(?:\.[0-9]+)?)</td>',market.group(1),re.S)
    selected=[tuple(float(x) for x in row[1:]) for row in odds if row[0]==book]
    if len(selected)!=1 or selected[0]!=item.decimal_odds_1x2:
        raise QuoteRefused("public bookmaker quote and captured prices disagree")
    return True


def _html_schedule_evidence(raw:bytes,item:MarketQuote):
    if item.schedule_source_url!=item.source_url or item.schedule_evidence_sha256!=item.evidence_sha256:
        raise QuoteRefused("public HTML reschedule must bind same source artifact")
    return _html_quoted_evidence(raw,item)


def _source_evidence(raw:bytes,item:MarketQuote):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_EVIDENCE_BYTES:
        raise QuoteRefused("source snapshot bytes missing or outside bounds")
    if sha256(raw).hexdigest()!=item.evidence_sha256:
        raise QuoteRefused("quote source evidence SHA-256 mismatch")
    if item.evidence_kind=="public_1x2_html":
        _html_quoted_evidence(raw,item)
        return
    try:
        x=json.loads(raw)
    except (ValueError,UnicodeError) as e:
        raise QuoteRefused("quoted source is not structured evidence JSON") from e
    if (not isinstance(x,dict) or x.get("type")!="wolf.provider-quote-observation.v1"
        or x.get("provider")!=item.provider or x.get("source_url")!=item.source_url
        or x.get("fixture_identity")!=item.fixture_identity
        or x.get("quoted_fixture_day")!=item.quoted_fixture_day
        or x.get("kickoff_utc")!=item.kickoff_utc
        or x.get("observed_utc")!=item.observed_utc
        or _prices(x.get("decimal_odds_1x2"))!=item.decimal_odds_1x2):
        raise QuoteRefused("source quote does not match typed capture")
    if x.get("financial_execution_authorized") is not False:
        raise QuoteRefused("quote source must not imply financial authority")


class QuoteBook:
    def __init__(self,source:dict):
        if source.get("forecast_digest_sha256")!=FORECAST_DIGEST:
            raise QuoteRefused("wrong frozen forecast")
        self.source=source
        self.ids={x["identity"]:x for x in source["records"]}
        self.records=[]
        self.by_id={}
        self.tail="0"*64

    def record(self,quote:MarketQuote,raw:bytes,*,schedule_raw:bytes|None=None,
               transport_raw:bytes|None=None):
        if not isinstance(quote,MarketQuote):
            raise QuoteRefused("typed quote required")
        if quote.capture_id in self.by_id:
            if self.by_id[quote.capture_id]["quote"]==_quote_dict(quote):
                return self.by_id[quote.capture_id]
            raise QuoteRefused("conflicting repeated quote identity")
        if quote.fixture_identity not in self.ids:
            raise QuoteRefused("quote for fixture outside original freeze")
        old_day=self.ids[quote.fixture_identity]["fixture_day"]
        if quote.observed_utc<="2026-11-26T00:00:00Z":
            raise QuoteRefused("source quote predates forecast cutoff")
        _source_evidence(raw,quote)
        if quote.transport_evidence_sha256 is not None:
            _transport_proof(transport_raw,quote)
        elif transport_raw is not None:
            raise QuoteRefused("unbound HTTP transport evidence refused")
        rescheduled=(old_day!=quote.quoted_fixture_day)
        if rescheduled:
            if quote.schedule_evidence_sha256 is None or quote.schedule_source_url is None or schedule_raw is None:
                raise QuoteRefused("rescheduled fixture requires explicit independent schedule evidence")
            if sha256(schedule_raw).hexdigest()!=quote.schedule_evidence_sha256:
                raise QuoteRefused("schedule evidence source SHA-256 mismatch")
            if quote.evidence_kind=="public_1x2_html":
                _html_schedule_evidence(schedule_raw,quote)
            else:
                try:
                    schedule=json.loads(schedule_raw)
                except (ValueError,UnicodeError) as e:
                    raise QuoteRefused("invalid schedule source") from e
                if not isinstance(schedule,dict) or schedule.get("type")!="wolf.public-schedule-evidence.v1" or schedule.get("source_url")!=quote.schedule_source_url or schedule.get("fixture_identity")!=quote.fixture_identity or schedule.get("current_kickoff_utc")!=quote.kickoff_utc:
                    raise QuoteRefused("schedule evidence contradicts revised fixture")
        elif any(v is not None for v in (schedule_raw,quote.schedule_source_url,quote.schedule_evidence_sha256)):
            raise QuoteRefused("extraneous schedule evidence")
        probability=[1/x for x in quote.decimal_odds_1x2]
        margin=sum(probability)-1
        record={"quote":_quote_dict(quote),"frozen_fixture_day":old_day,
                "schedule_changed":rescheduled,
                "market_de_vig_1x2":[round(v/sum(probability),12) for v in probability],
                "market_overround":round(margin,12),
                "source_trust":"SELF_REPORTED_CAPTURE_WITH_LOCAL_SHA256_ONLY",
                "independent_provider_authentication":False,
                "price_executable_at_provider":False,
                "financial_action_authorized":False}
        if quote.transport_evidence_sha256 is not None:
            record["transport_header_date_bound"] = True
        if margin < -0.10 or margin > 0.85:
            raise QuoteRefused("implausible three-way market overround")
        envelope={"sequence":len(self.records)+1,"previous_sha256":self.tail,
                  "record":record}
        envelope["sha256"]=digest(envelope)
        self.records.append(envelope)
        self.by_id[quote.capture_id]=record
        self.tail=envelope["sha256"]
        return record

    def snapshot(self):
        result={"schema":SCHEMA,"original_forecast_digest_sha256":FORECAST_DIGEST,
                "original_forecast_source_sha256":SOURCE_SHA,
                "records":self.records,"last_sha256":self.tail,
                "no_funding_authority":True,
                "independent_authentication_incomplete":True}
        result["seal_sha256"]=digest(result)
        return result

    @classmethod
    def replay(cls,source:dict,state:dict, evidence_dir:Path):
        expected=dict(state)
        seal=expected.pop("seal_sha256",None)
        if seal!=digest(expected) or expected.get("schema")!=SCHEMA or expected.get("original_forecast_digest_sha256")!=FORECAST_DIGEST:
            raise QuoteRefused("quote journal seal mismatch")
        entries=expected.get("records")
        if not isinstance(entries,list) or len(entries)>270*20:
            raise QuoteRefused("quote journal count outside bounds")
        obj=cls(source)
        for envelope in entries:
            if not isinstance(envelope,dict) or envelope.get("sequence")!=len(obj.records)+1 or envelope.get("previous_sha256")!=obj.tail:
                raise QuoteRefused("quote journal sequence gap")
            entry=dict(envelope)
            if entry.pop("sha256",None)!=digest(entry):
                raise QuoteRefused("quote event digest mismatch")
            typed=MarketQuote(**envelope["record"]["quote"])
            ext=".html" if typed.evidence_kind=="public_1x2_html" else ".json"
            raw=(evidence_dir/(typed.evidence_sha256+ext)).read_bytes()
            if envelope["record"]["schedule_changed"]:
                schedule_raw=(evidence_dir/(typed.schedule_evidence_sha256+ext)).read_bytes()
            else:
                schedule_raw=None
            transport=(evidence_dir/(typed.transport_evidence_sha256+".headers")).read_bytes() if typed.transport_evidence_sha256 else None
            result=obj.record(typed,raw,schedule_raw=schedule_raw,transport_raw=transport)
            if result!=envelope["record"]:
                raise QuoteRefused("quote event semantic replay mismatch")
        if obj.snapshot()!=state:
            raise QuoteRefused("quote journal state replay mismatch")
        return obj


def immutable(path:Path,data:bytes):
    p=path.resolve()
    if not p.parent.is_dir() or p.parent.stat().st_mode & 0o077:
        raise QuoteRefused("owner-only existing evidence directory required")
    if not isinstance(data,bytes) or len(data)>MAX_EVIDENCE_BYTES*4:
        raise QuoteRefused("invalid evidence size")
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    return sha256(data).hexdigest()
