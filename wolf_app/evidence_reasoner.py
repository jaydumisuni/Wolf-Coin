"""Website-neutral observation reasoning for Wolf Browser.

Turns authenticated *normalized evidence* into typed facts, relationships and
a proposed next task. No website allowlist, selector recipes, URL matching or
platform APIs. Unknown labels are preserved, not called unsupported.

This is deterministic text-vector and numeric reasoning, not proof of a
trained general agent or a profitable strategy. The native host owns the
website, authentication, screenshots and execution.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from math import sqrt, log
import re
from urllib.parse import urlparse

from wolf_core.contracts import ContractError
from .contracts import obj, time, currency

SCHEMA = "wolf.browser.evidence.v1"
RESULT = "wolf.app.observation-reasoning.v1"
TOKENS = re.compile(r"(?u)[^\W_]+")
MONEY = re.compile(
    r"^\s*(?:(?P<prefix>[A-Z]{3}|[$€£]|K|ZK)\s*)?"
    r"(?P<value>[+-]?(?:\d{1,3}(?:,\d{3})+|\d{1,15})(?:\.\d{1,6})?)"
    r"\s*(?P<suffix>[A-Z]{3})?\s*$")
HASH = re.compile(r"[0-9a-f]{64}\Z")
SENSITIVE = re.compile(
    r"(?:passw(?:or)?d|passcode|otp|one.time|secret|token|api.?key|"
    r"private.?key|recovery.?code|credit.?card|cvv|session.?id)",
    re.I)

# These are domain concepts, NOT site-specific selectors or website rules.
CONCEPTS = {
    "available_balance": ("available balance","available funds","usable funds",
                          "spendable wallet","available cash","wallet balance"),
    "cash_balance": ("balance","cash balance","total balance","wallet total",
                     "total funds","account balance","account wallet"),
    "pending_bets": ("pending bets","unsettled stakes","pending wagers",
                     "outstanding bets","pending tickets"),
    "pending_deposits": ("pending deposits","incoming deposit"),
    "pending_withdrawals": ("pending withdrawal","withdrawal pending"),
    "open_exposure": ("open exposure","open positions","current liability",
                      "margin used","active risk"),
    "realized_pnl": ("realized pnl","net profit loss","net profit","profit loss",
                     "closed pnl","settled profit","realised gain","net gains"),
    "unrealized_pnl": ("unrealized pnl","floating profit","unrealized loss",
                       "open pnl","unrealised profit"),
    "fees_total": ("total fees","commission paid","total commission","fees paid"),
    "odds": ("odds","decimal odds","betting price","market quote",
             "quotation","offer price","quoted price"),
    "account_equity": ("equity","account equity","portfolio equity"),
    "instrument": ("instrument","symbol","market","fixture","contract"),
}
ACTION_PROTOTYPES = {
    "SIGN_IN": ("sign in","login","log in","continue account"),
    "SIGN_OUT": ("sign out","log out","logout"),
    "OBSERVE_ACCOUNT": ("wallet","account","portfolio","transactions","my bets"),
    "PLACE_BET": ("place bet","bet now","confirm stake","submit wager"),
    "CANCEL_BET": ("cancel bet","cash out bet"),
    "PLACE_TRADE": ("place trade","submit order","buy now","sell now","trade"),
    "CLOSE_POSITION": ("close position","exit trade","close trade"),
    "NAVIGATE": ("open link","navigate","visit page"),
}
FINANCIAL_FIELDS = frozenset(CONCEPTS) - {"odds","instrument","account_equity"}
SYNONYMS = {
    "funds":"fund", "wagers":"bet", "wager":"bet",
    "bets":"bet", "stakes":"stake", "tickets":"ticket",
    "profits":"profit", "losses":"loss","positions":"position",
    "quotes":"quote","prices":"price","balances":"balance",
    "gains":"gain","unsettled":"pending",
    "wallets":"wallet","realised":"realized","unrealised":"unrealized",
}
MAX_ELEMENTS = 250
MAX_CONTROLS = 120
MAX_OPPORTUNITIES = 80


def _tokens(value: str) -> Counter:
    if type(value) is not str or len(value)>180:
        raise ContractError("bounded semantic label required")
    words=[SYNONYMS.get(x.lower(),x.lower())
           for x in TOKENS.findall(re.sub(r"([a-z])([A-Z])",r"\1 \2",value))]
    return Counter(w for w in words if len(w)>1)


def _cosine(a: Counter,b: Counter,weight: dict[str,float]) -> float:
    common=set(a)&set(b)
    dot=sum(a[x]*b[x]*weight.get(x,1.0)**2 for x in common)
    na=sqrt(sum((n*weight.get(x,1.0))**2 for x,n in a.items()))
    nb=sqrt(sum((n*weight.get(x,1.0))**2 for x,n in b.items()))
    return dot/(na*nb) if na and nb else 0.0


def _match(label: str, concepts: dict[str,tuple[str,...]],
           inverse_frequency: dict[str,float]) -> tuple[str|None,float]:
    observed=_tokens(label)
    if not observed:
        return None,0.0
    ranked=sorted((
        (max(_cosine(observed,_tokens(phrase),inverse_frequency)
             for phrase in alternatives),name)
        for name,alternatives in concepts.items()
    ),reverse=True)
    top_score,top_name=ranked[0]
    next_score=ranked[1][0] if len(ranked)>1 else 0
    if top_score < 0.53 or top_score-next_score < 0.04:
        return None,round(top_score,5)
    return top_name,round(top_score,5)


def _number(value: str, hint: str|None) -> dict|None:
    if type(value) is not str or len(value)>100:
        raise ContractError("bounded value expected")
    match=MONEY.fullmatch(value)
    if not match:
        return None
    raw=match["value"].replace(",","")
    try:
        number=Decimal(raw)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    code=match["suffix"]
    prefix=match["prefix"]
    if code and prefix in ("USD","ZMW","GBP","EUR") and code!=prefix:
        return None
    code=code or (prefix if prefix and len(prefix)==3 and prefix.isalpha() else None)
    if not code and prefix in ("K","ZK"):
        code="ZMW" if hint=="ZMW" else None
    if not code and prefix=="$":
        # The dollar sign is not exclusively USD. Avoid silently relabeling
        # it as a different account currency (e.g. ZMW).
        code=hint if hint in ("USD","CAD","AUD","NZD","SGD","HKD") else None
    if not code and prefix=="€":
        code="EUR"
    if not code and prefix=="£":
        code="GBP"
    unresolved_symbol=prefix in ("$","K","ZK") and code is None
    return {"decimal":str(number),"currency":code or (None if unresolved_symbol else hint),
            "explicit_currency":bool(code)}


def _weight_profile(labels: list[str]) -> dict[str,float]:
    docs=[set(_tokens(label)) for label in labels]
    corpus=len(docs)+1
    counts=Counter(t for terms in docs for t in terms)
    # IDF highlights structurally distinctive labels on an unfamiliar page.
    return {term:1+log(corpus/(1+count)) for term,count in counts.items()}


def interpret(document: dict) -> dict:
    obj(document,{"schema","origin","observed_at","evidence_sha256","elements","controls"},
        {"title","browser_auth_state","currency_hint","opportunities","account_id",
         "dom_controls_match_current_page"})
    if document["schema"]!=SCHEMA:
        raise ContractError("unsupported normalized browser evidence")
    raw_origin=document["origin"]
    if type(raw_origin) is not str or len(raw_origin)>253:
        raise ContractError("origin hostname must be bounded")
    parsed=urlparse("//"+raw_origin)
    if (parsed.hostname!=raw_origin or not parsed.hostname or parsed.username
        or parsed.password or parsed.port or "/" in raw_origin or "@" in raw_origin):
        raise ContractError("hostname only; no URL credentials or paths")
    if not HASH.fullmatch(document["evidence_sha256"]):
        raise ContractError("evidence hash must be SHA-256 hex")
    observed_at=time(document["observed_at"])
    now=datetime.now(timezone.utc)
    observed=datetime.fromisoformat(observed_at)
    stale=(now-observed).total_seconds()>300
    auth=document.get("browser_auth_state","unverified")
    if auth not in ("login_required","probable_authenticated","unverified","expired","offline"):
        raise ContractError("unknown browser auth observation")
    hint=document.get("currency_hint")
    if hint is not None:
        hint=currency(hint)
    account_id=document.get("account_id")
    if account_id is not None and (
       type(account_id) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}",account_id)):
        raise ContractError("invalid local account identity")
    elements=document["elements"]
    controls=document["controls"]
    opportunities=document.get("opportunities",[])
    if (type(elements) is not list or len(elements)>MAX_ELEMENTS or
        type(controls) is not list or len(controls)>MAX_CONTROLS or
        type(opportunities) is not list or len(opportunities)>MAX_OPPORTUNITIES):
        raise ContractError("bounded observation arrays required")
    all_labels=[]
    for entry in elements:
        obj(entry,{"label","value"},{"context"})
        if any(type(entry[x]) is not str for x in entry):
            raise ContractError("string-only normalized observation fields")
        if any(SENSITIVE.search(entry[x]) for x in entry):
            raise ContractError("possible secret field in observation")
        if len(entry["context"])>140 if "context" in entry else False:
            raise ContractError("context too long")
        all_labels.append(entry["label"]+" "+entry.get("context",""))
    for item in controls:
        obj(item,{"label"},{"role","target_ref"})
        if any(type(item[x]) is not str for x in item):
            raise ContractError("invalid control")
        if any(SENSITIVE.search(item[x]) for x in item):
            raise ContractError("secret control")
        all_labels.append(item["label"])
    weights=_weight_profile(all_labels or ["unknown"])

    facts=[]
    relationships=[]
    collisions=defaultdict(list)
    for i,item in enumerate(elements):
        label=item["label"]
        key,score=_match(label+" "+item.get("context",""),CONCEPTS,weights)
        numeric=_number(item["value"],hint)
        normalized={
            "node_id":f"field_{i}",
            "type":"NUMERIC" if numeric else "UNKNOWN_OR_TEXT",
            "semantic_type":key or "UNCLASSIFIED",
            "semantic_score":score,
            "label":label[:140],
            "context":item.get("context","")[:140],
            "decimal":numeric["decimal"] if numeric else None,
            "currency":(
                None if key in ("odds","instrument") else
                numeric["currency"] if numeric else None),
            "text_value":None if numeric else item["value"][:100],
            "evidence_sha256":document["evidence_sha256"],
        }
        facts.append(normalized)
        if key and numeric:
            relationships.append({"from":f"field_{i}","relationship":"MEASURES",
                                  "to":key})
            collisions[(key,numeric["currency"])].append(numeric["decimal"])
    inconsistencies=[
        {"concept":key,"currency":code,"status":"CONFLICTING_OBSERVATIONS"}
        for (key,code),nums in collisions.items()
        if len({Decimal(number) for number in nums})>1
    ]
    actions=[]
    for i,control in enumerate(controls):
        name,score=_match(control["label"],ACTION_PROTOTYPES,weights)
        actions.append({
            "node_id":f"control_{i}",
            "observed_role":control.get("role","unknown")[:60],
            "semantic_action":name or "GENERAL_INTERACTION",
            "semantic_score":score,
            "label":control["label"][:140],
            "target_ref":control.get("target_ref"),
            "requires_current_page_readback":True,
        })
    market=[]
    for i,item in enumerate(opportunities):
        obj(item,{"market","selection","kind","side","quote","currency"})
        if any(type(item[key]) is not str for key in item):
            raise ContractError("normalized market fields must be strings")
        if any(len(v)>140 or SENSITIVE.search(v) for v in item.values()):
            raise ContractError("invalid market value")
        if item["kind"] not in ("bet","trade") or item["side"] not in ("back","buy","sell"):
            raise ContractError("invalid market kind/side")
        code=currency(item["currency"])
        try:
            odds=Decimal(item["quote"])
        except InvalidOperation as exc:
            raise ContractError("invalid quote") from exc
        if not odds.is_finite() or odds<=0 or odds>Decimal("1000000000"):
            raise ContractError("quote out of scope")
        # Decimal odds imply a probability only for back bets, not for a
        # stock/FX price. No model probability => cannot calculate edge.
        implied=str((Decimal(1)/odds).quantize(Decimal("0.000001"))) if (
            item["kind"]=="bet" and item["side"]=="back" and odds>1) else None
        market.append({
            "node_id":f"market_{i}",
            "market":item["market"],"selection":item["selection"],
            "kind":item["kind"],"side":item["side"],
            "quote":str(odds),"currency":code,
            "market_implied_probability":implied,
            "forecast_probability":None,
            "edge_verified":False,
            "evidence_sha256":document["evidence_sha256"],
        })
    field_finance=sum(1 for f in facts if f["semantic_type"] in FINANCIAL_FIELDS and f["decimal"])
    has_markets=bool(market) or any(f["semantic_type"]=="odds" for f in facts)
    has_account=bool(account_id)
    if auth in ("login_required","expired"):
        task="RESTORE_AUTHENTICATED_SESSION";why="website reports login or expiry"
    elif auth=="offline":
        task="WAIT_FOR_CONNECTIVITY";why="website observation is offline"
    elif stale:
        task="REFRESH_BROWSER_OBSERVATION";why="source observation is stale"
    elif auth=="unverified" and field_finance:
        task="VERIFY_SESSION_AND_ACCOUNT";why="financial fields without confirmed session context"
    elif field_finance and not has_account:
        task="REGISTER_OR_SELECT_ACCOUNT";why="financial facts need a persistent account association"
    elif inconsistencies:
        task="RECONCILE_CONFLICTED_FINANCIAL_STATE";why="multiple differing values for one fact"
    elif has_markets:
        ready=bool(market)
        task=("EVALUATE_MARKET_WITH_MODELS" if ready
              else "DISCOVER_MARKET_AND_SELECTION_IDENTITIES")
        why=("market selection and quote are available; apply existing "
             "model and cost math" if ready else
             "price-like evidence found; resolve its instrument, selection "
             "and quote type before model evaluation")
    elif field_finance:
        task="SYNC_FINANCES";why="financial observations can be reconciled"
    elif actions:
        task="INSPECT_SITE_CAPABILITIES";why="control semantics available for browser planning"
    else:
        task="ORGANIZE_NEW_SITE_EVIDENCE";why="unknown evidence remains available for learning"
    return {
        "schema":RESULT,
        "origin":raw_origin,
        "observed_at":observed_at,
        "evidence_sha256":document["evidence_sha256"],
        "source":"NATIVE_BROWSER_NORMALIZED_OBSERVATION",
        "goal_discovered_without_user_provided_goal":True,
        "next_task":task,
        "reason":why,
        "facts":facts,
        "controls":actions,
        "dom_controls_match_current_page":
            document.get("dom_controls_match_current_page",True),
        "markets":market,
        "relationships":relationships,
        "conflicts":inconsistencies,
        "unclassified_count":sum(f["semantic_type"]=="UNCLASSIFIED" for f in facts),
        "site_specific_adapter_used":False,
        "market_probability_math_available":bool(
            market and any(item["market_implied_probability"] for item in market)),
        "model_forecast_connected":False,
        "native_browser_action_executed":False,
        "money_action_executed":False,
    }
