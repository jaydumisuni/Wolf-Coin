"""Single website-neutral translator for the existing wolf.browser.v1 frontend.

Receives the native Chromium host's candidate-only page snapshot and emits
bounded normalized facts for the signed observation.discover operation.
No platform-specific URLs, selectors, recipes or credentials are needed.
"""
from __future__ import annotations
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
import json,re
from urllib.parse import urlparse
from wolf_core.contracts import ContractError
from .evidence_reasoner import SCHEMA,MONEY,SENSITIVE

LINE_LIMIT=180
CANDIDATE_NAMES={"balance":"Available Balance","pending":"Pending Bets",
                 "pnl":"Realized Profit Loss"}
SEPARATOR=re.compile(r"^([^:\n]{2,100}?)\s*:\s*(.{1,80})$")

def _valid_line(text):
    line=" ".join(str(text).split()).strip()
    if len(line)>140 or SENSITIVE.search(line):
        return None
    return line or None

def _number_string(value):
    if type(value) in (int,float,Decimal):
        try:
            n=Decimal(str(value))
        except Exception:
            return None
        if n.is_finite() and abs(n)<Decimal("1e15"):
            return str(n)
    if type(value) is str and MONEY.fullmatch(value):
        return value
    return None

def normalize_browser_snapshot(snapshot:dict,dom:dict|None=None)->dict:
    if type(snapshot) is not dict or snapshot.get("contract")!="wolf.browser.v1":
        raise ContractError("wolf.browser.v1 snapshot required")
    url=snapshot.get("url")
    if type(url) is not str or len(url)>2048:
        raise ContractError("invalid browser URL")
    parsed=urlparse(url)
    if parsed.scheme not in ("https","http") or not parsed.hostname:
        raise ContractError("unexpected browser URL scheme")
    if parsed.username or parsed.password or parsed.fragment:
        raise ContractError("browser URL includes sensitive material")
    if parsed.scheme=="http" and parsed.hostname not in ("localhost","127.0.0.1","::1"):
        raise ContractError("unencrypted nonlocal browser URL")
    origin=parsed.hostname
    observed=snapshot.get("observedAt")
    if type(observed) is not str:
        raise ContractError("observedAt required")
    auth=snapshot.get("auth","unverified")
    if auth not in ("probable_authenticated","login_required","unverified","expired","offline"):
        raise ContractError("unknown observed session state")
    account=snapshot.get("accountId")
    if type(account) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}",account):
        raise ContractError("browser local account identity required")
    fields=[]
    hints=set()
    candidates=snapshot.get("candidates",{})
    if type(candidates) is not dict:
        raise ContractError("invalid candidates")
    for name in CANDIDATE_NAMES:
        candidate=candidates.get(name)
        if candidate is None:
            continue
        if type(candidate) is not dict or candidate.get("verification") not in (
                "candidate_only","browser_observation_only"):
            continue
        label=_valid_line(candidate.get("source") or CANDIDATE_NAMES[name])
        value=_number_string(candidate.get("value"))
        curr=candidate.get("currency")
        if type(curr) is str and re.fullmatch("[A-Z]{3}",curr):
            hints.add(curr)
            if value is not None:
                marker=MONEY.fullmatch(value) if type(value) is str else None
                if marker and not marker.group("prefix") and not marker.group("suffix"):
                    value=curr+" "+value
        if label and value is not None:
            fields.append({"label":label,"value":value})
    raw=snapshot.get("visibleText","")
    if type(raw) is not str or len(raw)>60000:
        raise ContractError("bounded visible text expected")
    # Keep blank/redacted lines as separators. Never join values across a
    # removed credential field or unrelated page section.
    lines=[_valid_line(x) for x in raw.splitlines()[:1000]]
    for i,line in enumerate(lines[:LINE_LIMIT]):
        if not line or len(fields)>=200:
            continue
        pair=SEPARATOR.fullmatch(line)
        if pair and (v:=_number_string(pair[2])) is not None:
            fields.append({"label":pair[1],"value":v})
        elif i+1<len(lines) and lines[i+1] and _number_string(line) is None:
            adjacent=lines[i+1]
            if (v:=_number_string(adjacent)) is not None:
                fields.append({"label":line,"value":v})
            elif (len(line)<=90 and len(adjacent)<=100 and
                  not SEPARATOR.fullmatch(adjacent)):
                # Unknown sites still expose text facts and relationships;
                # keep them as candidates, not silently discarded.
                fields.append({"label":line,"value":adjacent})
    controls=[]
    dom_matched=True
    if dom is not None:
        if type(dom) is not dict or dom.get("accountId")!=account:
            raise ContractError("DOM inspection belongs to a different account")
        nodes=dom.get("nodes")
        if type(nodes) is not list or len(nodes)>250:
            raise ContractError("bounded DOM control inventory required")
        if "url" in dom and dom["url"]!=url:
            dom_matched=False
        if "observedAt" in dom:
            try:
                browser_when=datetime.fromisoformat(str(observed).replace("Z","+00:00"))
                dom_when=datetime.fromisoformat(str(dom["observedAt"]).replace("Z","+00:00"))
                if (browser_when.tzinfo is None or dom_when.tzinfo is None or
                    abs((browser_when-dom_when).total_seconds())>30):
                    dom_matched=False
            except ValueError:
                dom_matched=False
        for item in nodes if dom_matched else []:
            if type(item) is not dict:
                raise ContractError("invalid DOM descriptor")
            label=_valid_line(item.get("text") or item.get("name") or "")
            if not label:
                continue
            role=str(item.get("role") or item.get("tag") or "control")
            if len(role)>60 or SENSITIVE.search(role):
                continue
            controls.append({"label":label,"role":role})
            if len(controls)>=120:
                break
    items=[]
    opportunities=snapshot.get("opportunities",[])
    if type(opportunities) is not list or len(opportunities)>80:
        raise ContractError("bounded market observations required")
    for item in opportunities:
        if type(item) is not dict:
            continue
        values={key:item.get(key) for key in
                ("market","selection","kind","side","quote","currency")}
        if not all(isinstance(values[k],str) for k in
                   ("market","selection","kind","side","currency")):
            continue
        q=_number_string(values["quote"])
        if not q:
            continue
        if any(SENSITIVE.search(str(v)) for v in values.values()):
            continue
        items.append({**values,"quote":q})
    doc={
        "schema":SCHEMA,
        "origin":origin,
        "observed_at":observed,
        "account_id":account,
        "browser_auth_state":auth,
        "elements":fields[:250],
        "controls":controls,
        "opportunities":items,
        "dom_controls_match_current_page":dom_matched,
    }
    if len(hints)==1:
        doc["currency_hint"]=next(iter(hints))
    raw_canonical=json.dumps(doc,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    # Vetted normalized content hash; not a signature of a source screenshot.
    doc["evidence_sha256"]=sha256(raw_canonical.encode()).hexdigest()
    return doc


def main(argv=None)->int:
    """Offline native-host transformer: browser snapshot -> safe app evidence."""
    import sys
    if argv not in (None,[],()):
        raise SystemExit(2)
    try:
        incoming=sys.stdin.buffer.read(110001)
        if len(incoming)>110000:
            raise ContractError("browser observation too large")
        from .contracts import obj
        source=json.loads(incoming)
        obj(source,{"snapshot"},{"dom"})
        result=normalize_browser_snapshot(source["snapshot"],source.get("dom"))
        print(json.dumps({"operation":"observation.discover",
                          "payload":{"document":result}},sort_keys=True,
                          separators=(",",":"),ensure_ascii=False))
        return 0
    except (ValueError,TypeError,ContractError) as exc:
        print(json.dumps({"status":"INVALID_OBSERVATION",
                          "error":type(exc).__name__}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
