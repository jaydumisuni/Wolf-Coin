"""Wolf-Coin situational capability selection, without global feature locks.

This is a *planner*, not a browser driver. It decides which capability fits
the current task, registered account, session, evidence, platform affordance,
and financial context. Missing context returns a recovery step, not an
arbitrary permanent disability. The native Wolf Browser host executes actions
and returns authoritative readback once integrated.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from wolf_core.contracts import ContractError
from .contracts import amount, ident, obj


INTELLIGENCE = frozenset({"LEARN", "RESEARCH", "ANALYZE", "COMPARE_STRATEGIES"})
BROWSER_GENERAL = {
    "OPEN_PLATFORM": "NAVIGATE",
    "READ_PAGE": "INSPECT",
    "CLICK_ELEMENT": "CLICK",
    "TYPE_TEXT": "TYPE",
    "SCROLL_PAGE": "SCROLL",
    "SWITCH_TAB": "SWITCH_TAB",
    "DOWNLOAD_FILE": "DOWNLOAD",
    "UPLOAD_FILE": "UPLOAD",
}
BROWSER_ACCOUNT = {
    "OBSERVE_ACCOUNT": "OBSERVE_ACCOUNT",
    "SYNC_FINANCES": "OBSERVE_ACCOUNT",
    "RECONCILE_ACTION": "INSPECT",
}
FINANCIAL = {
    "PLACE_BET": ("sports", "PLACE_BET"),
    "CANCEL_BET": ("sports", "CANCEL_BET"),
    "PLACE_TRADE": ("trading", "PLACE_TRADE"),
    "CLOSE_POSITION": ("trading", "CLOSE_POSITION"),
}
GOALS = INTELLIGENCE | frozenset(BROWSER_GENERAL) | frozenset(BROWSER_ACCOUNT) | frozenset(FINANCIAL)
AFFORDANCES = frozenset(BROWSER_GENERAL.values()) | frozenset(BROWSER_ACCOUNT.values()) | frozenset(x[1] for x in FINANCIAL.values())
PERMISSIONS = frozenset({"OBSERVE", "INTERACT", "TRANSACT"})


def _result(goal: str, *, family: str, state: str, next_step: str,
            capabilities: list[str] | None = None, reasons: list[str] | None = None,
            handoff: dict | None = None, financial: bool = False) -> dict:
    return {
        "schema": "wolf.app.context-route.v1",
        "goal": goal,
        "family": family,
        "state": state,
        "next_step": next_step,
        "required_capabilities": capabilities or [],
        "context_reasons": reasons or [],
        "native_browser_handoff": handoff,
        "financial_action": financial,
        "global_feature_lock": False,
        "selected_by_context": True,
        "browser_action_executed": False,
        "order_or_bet_submitted": False,
        "requires_native_host_result": handoff is not None,
    }


def route_context(*, goal: str, account: dict | None,
                  capabilities: list[str], permissions: list[str],
                  target: str | None = None, requested_amount: str | None = None,
                  money_budget: str | None = None) -> dict:
    if type(goal) is not str or goal not in GOALS:
        raise ContractError("unknown context goal")
    if not isinstance(capabilities, list) or len(capabilities) > 32 or any(
        type(c) is not str or c not in AFFORDANCES for c in capabilities
    ):
        raise ContractError("invalid reported browser affordances")
    if not isinstance(permissions, list) or len(permissions) > 3 or any(
        type(p) is not str or p not in PERMISSIONS for p in permissions
    ):
        raise ContractError("invalid host permission list")
    if len(set(capabilities))!=len(capabilities) or len(set(permissions))!=len(permissions):
        raise ContractError("duplicate host capability")
    if target is not None:
        ident(target,"browser target identity")
    if requested_amount is not None:
        amount(requested_amount,nonnegative=True)
    if money_budget is not None:
        amount(money_budget,nonnegative=True)

    if goal in INTELLIGENCE:
        return _result(goal,family="INTELLIGENCE",state="READY",
                       next_step="INTELLIGENCE_EVALUATE",
                       reasons=["research and learning do not require an authenticated platform"],
                       handoff={"kind":"INTELLIGENCE_EVALUATE","goal":goal,
                                "input":"SCOPED_RESEARCH_EVIDENCE"})

    if goal in BROWSER_GENERAL:
        needed = BROWSER_GENERAL[goal]
        if needed not in capabilities:
            return _result(goal,family="BROWSER",state="DISCOVER",
                           next_step="INSPECT_BROWSER_CAPABILITIES",
                           capabilities=[needed],
                           reasons=["browser has not reported this affordance"])
        if "INTERACT" not in permissions and needed not in ("INSPECT","NAVIGATE"):
            return _result(goal,family="BROWSER",state="RECOVER",
                           next_step="CONFIRM_BROWSER_INTERACTION_PERMISSION",
                           capabilities=[needed],
                           reasons=["native host did not confirm scope for this site"])
        if needed=="INSPECT" and "OBSERVE" not in permissions:
            return _result(goal,family="BROWSER",state="RECOVER",
                           next_step="CONFIRM_BROWSER_OBSERVATION_PERMISSION",
                           capabilities=[needed])
        if needed in ("CLICK","TYPE","UPLOAD","DOWNLOAD") and target is None:
            return _result(goal,family="BROWSER",state="DISCOVER",
                           next_step="IDENTIFY_PAGE_TARGET",
                           capabilities=[needed],
                           reasons=["element/file target not resolved"])
        return _result(goal,family="BROWSER",state="READY",
                       next_step="HANDOFF_TO_WOLF_BROWSER",
                       capabilities=[needed],
                       reasons=["native browser capability and site scope matched"],
                       handoff={"kind":needed,"target_id":target,
                                "requires_current_site_state":True})

    if not account:
        return _result(goal,family="FINANCIAL" if goal in FINANCIAL else "ACCOUNT",
                       state="RECOVER",next_step="REGISTER_OR_SELECT_ACCOUNT",
                       reasons=["operation needs a registered scoped account"],
                       financial=goal in FINANCIAL)
    domain=account.get("domain")
    state=account.get("session_state")
    freshness=account.get("freshness")
    if goal in FINANCIAL and FINANCIAL[goal][0]!=domain:
        raise ContractError("financial action incompatible with selected account domain")
    if state!="ACTIVE":
        return _result(goal,family="FINANCIAL" if goal in FINANCIAL else "ACCOUNT",
                       state="RECOVER",next_step="RESTORE_AUTHENTICATED_SESSION",
                       reasons=["account retained; browser session needs renewal"],
                       financial=goal in FINANCIAL)

    if goal in BROWSER_ACCOUNT:
        needed=BROWSER_ACCOUNT[goal]
        if needed not in capabilities:
            return _result(goal,family="ACCOUNT",state="DISCOVER",
                           next_step="INSPECT_BROWSER_CAPABILITIES",
                           capabilities=[needed])
        if "OBSERVE" not in permissions:
            return _result(goal,family="ACCOUNT",state="RECOVER",
                           next_step="CONFIRM_BROWSER_OBSERVATION_PERMISSION",
                           capabilities=[needed])
        if goal=="SYNC_FINANCES" and freshness=="CURRENT_UNVERIFIED":
            return _result(goal,family="ACCOUNT",state="READY",
                           next_step="RECONCILE_CURRENT_OBSERVATIONS",
                           capabilities=[needed],
                           reasons=["fresh account observations available"],
                           handoff={"kind":"RECONCILE","account_id":account["account_id"]})
        return _result(goal,family="ACCOUNT",state="READY",
                       next_step="HANDOFF_TO_WOLF_BROWSER",
                       capabilities=[needed],
                       handoff={"kind":needed,"account_id":account["account_id"],
                                "requires_new_observation":True})

    needed=FINANCIAL[goal][1]
    if needed not in capabilities:
        return _result(goal,family="FINANCIAL",state="DISCOVER",
                       next_step="INSPECT_PLATFORM_TRANSACTION_CAPABILITY",
                       capabilities=[needed],financial=True,
                       reasons=["no supported transaction affordance established for current website"])
    if "TRANSACT" not in permissions:
        return _result(goal,family="FINANCIAL",state="RECOVER",
                       next_step="CONFIRM_SITE_TRANSACTION_PERMISSION",
                       capabilities=[needed],financial=True)
    if freshness not in ("NO_OBSERVATION","STALE_LAST_KNOWN",
                         "CONFLICTED_UNVERIFIED","CURRENT_UNVERIFIED"):
        return _result(goal,family="FINANCIAL",state="DISCOVER",
                       next_step="VERIFY_ACCOUNT_EVIDENCE_STATE",
                       capabilities=[needed],financial=True)
    if freshness in ("NO_OBSERVATION","STALE_LAST_KNOWN"):
        return _result(goal,family="FINANCIAL",state="RECOVER",
                       next_step="OBSERVE_CURRENT_FINANCIAL_STATE",
                       capabilities=[needed],financial=True)
    if freshness=="CONFLICTED_UNVERIFIED":
        return _result(goal,family="FINANCIAL",state="RECOVER",
                       next_step="RECONCILE_CONFLICTED_FINANCIAL_STATE",
                       capabilities=[needed],financial=True)
    if goal in ("CANCEL_BET","CLOSE_POSITION"):
        # Cancel/close can reduce outstanding risk. A position identity and
        # current site state matter here, not a new spending allowance.
        if target is None:
            return _result(goal,family="FINANCIAL",state="DISCOVER",
                           next_step="IDENTIFY_EXISTING_BET_OR_POSITION",
                           capabilities=[needed],financial=True)
        return _result(goal,family="FINANCIAL",state="READY",
                       next_step="HANDOFF_TO_NATIVE_FINANCIAL_WORKFLOW",
                       capabilities=[needed],financial=True,
                       reasons=["scoped cancellation/close requested for an existing position"],
                       handoff={"kind":needed,"account_id":account["account_id"],
                                "domain":domain,"target_id":target,
                                "account_currency":account["currency"],
                                "requires_quote_and_risk_readback":True,
                                "requires_platform_result":True})
    if requested_amount is None or money_budget is None:
        return _result(goal,family="FINANCIAL",state="DISCOVER",
                       next_step="DETERMINE_ACTION_SIZE_AND_SCOPED_BUDGET",
                       capabilities=[needed],financial=True)
    proposed=Decimal(amount(requested_amount,nonnegative=True))
    budget=Decimal(amount(money_budget,nonnegative=True))
    if proposed<=0 or proposed>budget:
        return _result(goal,family="FINANCIAL",state="RECOVER",
                       next_step="RESIZE_ACTION_WITHIN_ACCOUNT_BUDGET",
                       capabilities=[needed],financial=True,
                       reasons=["proposed amount does not match the scoped risk budget"])
    return _result(goal,family="FINANCIAL",state="READY",
                   next_step="HANDOFF_TO_NATIVE_FINANCIAL_WORKFLOW",
                   capabilities=[needed],financial=True,
                   reasons=["account, session, site affordance, scoped permission and amount agree"],
                   handoff={"kind":needed,"account_id":account["account_id"],
                            "domain":domain,"target_id":target,
                            "requested_amount":str(proposed),
                            "account_currency":account["currency"],
                            "requires_quote_and_risk_readback":True,
                            "requires_platform_result":True})
