"""Wolf-Coin money-pilot preflight. It does NOT authorize funding.

Reports exact current engineering claims and unresolved external obligations.
Never accepts credentials, initiates deposits or lifts a live-authorization gate.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import json

from wolf_core.contracts import AccountScope, Domain
from wolf_funding.provider import ProviderCategory, ProviderReview, AutomationRight, assess
from wolf_funding.reconcile import FundingPolicy

def describe(domain: Domain, *, name: str = "unselected") -> dict:
    scope = AccountScope(domain,"pilot-1")
    category=ProviderCategory.SPORTSBOOK if domain is Domain.SPORTS else ProviderCategory.MT5_BROKER
    provider=ProviderReview(name,scope,category,"unknown",
                            automation_right=AutomationRight.UNKNOWN)
    check=assess(provider)
    limit=FundingPolicy().ceiling(domain)
    return {
        "schema":"wolf.funding-readiness.v1",
        "domain":domain.value,
        "candidate_provider":provider.provider_id,
        "pilot_budget_ZMW":str(limit),
        "total_planned_budget_ZMW":"200",
        "notional_risk_per_action_cap_ZMW":str(check.risk_ceiling),
        "max_customer_deposit_authorized_ZMW":"0",
        "live_mode_allowed":False,
        "funding_permitted":False,
        "transfer_adapters":0,
        "provider_connected":False,
        "provider_review":check.review_status,
        "external_blockers":list(check.reasons)+[
            "actual-provider-selected-and-connected",
            "actual-money-rail-and-authoritative-statement-proof",
            "independent-strategy-and-venue-recovery-qualification",
            "owner-signed-final-policy-and-independent-release",
        ],
        "failure_mode":"FAIL_CLOSED",
        "note":"K100 is a proposed cap, not an amount deposited or a reason to increase risk.",
    }


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog="wolf-funding-readiness",
                                   description="Read-only K100 pilot and provider funding gate report")
    parser.add_argument("--domain",required=True,choices=["sports","trading"])
    parser.add_argument("--provider-id",default="unselected")
    args=parser.parse_args(argv)
    from wolf_core.contracts import identifier
    identifier(args.provider_id)
    print(json.dumps(describe(Domain(args.domain),name=args.provider_id),sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
