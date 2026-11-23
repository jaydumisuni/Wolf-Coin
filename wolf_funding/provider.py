"""Provider admission research ledger; no authentication or transactions.

A provider with publicly advertised trading/betting cannot be assumed to permit
automated money execution. Self-attested booleans never mint a live release.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from wolf_core.contracts import AccountScope, ContractError, Domain, identifier, money
from wolf_funding.reconcile import FundingPolicy


class AutomationRight(str, Enum):
    UNKNOWN = "UNKNOWN"
    PROHIBITED = "PROHIBITED"
    READ_ONLY = "READ_ONLY"
    DEMO_ONLY = "DEMO_ONLY"
    LIVE_EXPLICIT = "LIVE_EXPLICIT"


class ProviderCategory(str, Enum):
    SPORTSBOOK = "SPORTSBOOK"
    BETTING_EXCHANGE = "BETTING_EXCHANGE"
    MT5_BROKER = "MT5_BROKER"
    DIRECT_BROKER_API = "DIRECT_BROKER_API"


@dataclass(frozen=True)
class ProviderReview:
    provider_id: str
    scope: AccountScope
    category: ProviderCategory
    interface_name: str
    automation_right: AutomationRight = AutomationRight.UNKNOWN
    official_terms_source: str = ""
    terms_reviewed_at: str = ""
    jurisdiction_confirmed: bool = False
    account_kyc_verified: bool = False
    actual_account_readback: bool = False
    source_rights_verified: bool = False
    execution_interface_verifiable: bool = False
    provider_minimum_stake: Decimal | None = None
    provider_currency: str = "ZMW"
    all_fees_verified: bool = False
    funding_method_verified: bool = False
    provider_suspended: bool = False

    def __post_init__(self):
        identifier(self.provider_id)
        identifier(self.interface_name)
        if type(self.category) is not ProviderCategory or type(self.automation_right) is not AutomationRight:
            raise ContractError("invalid provider category or automation permission type")
        if self.scope.domain is Domain.SPORTS and self.category not in (ProviderCategory.SPORTSBOOK,ProviderCategory.BETTING_EXCHANGE):
            raise ContractError("non-sports venue assigned to sports bankroll")
        if self.scope.domain is Domain.TRADING and self.category not in (ProviderCategory.MT5_BROKER,ProviderCategory.DIRECT_BROKER_API):
            raise ContractError("non-trading venue assigned to trading bankroll")
        if self.provider_minimum_stake is not None:
            object.__setattr__(self,"provider_minimum_stake",money(self.provider_minimum_stake,positive=True))
        if not isinstance(self.provider_currency,str) or len(self.provider_currency)!=3 or not self.provider_currency.isupper():
            raise ContractError("invalid provider currency")
        for flag in ("jurisdiction_confirmed","account_kyc_verified","actual_account_readback",
                     "source_rights_verified","execution_interface_verifiable",
                     "all_fees_verified","funding_method_verified","provider_suspended"):
            if type(getattr(self,flag)) is not bool:
                raise ContractError("invalid provider verification flag")


@dataclass(frozen=True)
class AdmissionAssessment:
    provider_id: str
    domain: str
    review_status: str
    reasons: tuple[str, ...]
    risk_ceiling: Decimal
    real_money_permitted: bool = False
    fund_transfer_enabled: bool = False
    provider_account_connected: bool = False


def assess(review: ProviderReview, *,
           policy: FundingPolicy = FundingPolicy()) -> AdmissionAssessment:
    """Detailed fail-closed assessment; never promotes to live automatically."""
    reasons=[]
    if review.provider_suspended:
        reasons.append("provider-suspended-or-limited")
    if review.automation_right is AutomationRight.PROHIBITED:
        reasons.append("provider-terms-prohibit-automation")
    elif review.automation_right is AutomationRight.UNKNOWN:
        reasons.append("provider-automation-permission-unknown")
    elif review.automation_right is AutomationRight.READ_ONLY:
        reasons.append("read-only-venue-access")
    elif review.automation_right is AutomationRight.DEMO_ONLY:
        reasons.append("demo-venue-access-only")
    if not review.official_terms_source or not review.terms_reviewed_at:
        reasons.append("official-terms-not-reviewed")
    if not review.jurisdiction_confirmed:
        reasons.append("jurisdiction-not-qualified")
    if not review.account_kyc_verified:
        reasons.append("account-kyc-not-verified")
    if not review.actual_account_readback:
        reasons.append("account-readback-not-proven")
    if not review.source_rights_verified:
        reasons.append("market-data-rights-unknown")
    if not review.execution_interface_verifiable:
        reasons.append("venue-effect-and-readback-interface-unproven")
    if review.provider_currency!=policy.currency:
        reasons.append("currency-fx-bridge-not-qualified")
    if review.provider_minimum_stake is None:
        reasons.append("provider-minimum-size-unverified")
    else:
        # Worst-case full stake can be lost in sports. Trading minimum loss
        # is not safely inferred from a minimum lot or notional; only an
        # independently measured broker loss profile may establish it.
        if review.scope.domain is Domain.SPORTS and review.provider_minimum_stake>policy.ceiling(Domain.SPORTS)*Decimal(".005"):
            reasons.append("minimum-stake-exceeds-paper-sports-cap")
        if review.scope.domain is Domain.TRADING:
            reasons.append("broker-minimum-loss-not-proven-by-minimum-volume")
    if not review.all_fees_verified:
        reasons.append("customer-fees-unverified")
    if not review.funding_method_verified:
        reasons.append("customer-funding-rail-unverified")
    # Even a complete applicant-provided record is not independent production
    # acceptance, owner signature or a credential-qualified executable adapter.
    if not reasons:
        reasons.append("independent-release-and-owner-signed-policy-not-proven")
    result=("DENIED" if (review.automation_right is AutomationRight.PROHIBITED
                         or review.provider_suspended) else "PENDING_EXTERNAL_PROOF")
    return AdmissionAssessment(review.provider_id,review.scope.domain.value,
                               result,tuple(reasons),
                               policy.ceiling(review.scope.domain)*Decimal(".0025") if review.scope.domain is Domain.TRADING
                               else policy.ceiling(review.scope.domain)*Decimal(".005"))
