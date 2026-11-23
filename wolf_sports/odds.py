"""Three-way football odds, overround and evidence-gated expected return."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from wolf_core.contracts import ContractError, identifier, money, utc_timestamp

OUTCOMES = ("home", "draw", "away")


@dataclass(frozen=True)
class ThreeWayQuote:
    provider: str
    fixture_id: str
    market_id: str
    observed_at: str
    prices: Mapping[str, Decimal]
    source_rights_confirmed: bool = False

    def __post_init__(self) -> None:
        identifier(self.provider)
        identifier(self.fixture_id)
        identifier(self.market_id)
        utc_timestamp(self.observed_at)
        if set(self.prices) != set(OUTCOMES):
            raise ContractError("three-way market requires home, draw and away")
        for value in self.prices.values():
            if money(value, positive=True) <= 1:
                raise ContractError("decimal market odds must exceed 1")
        if not isinstance(self.source_rights_confirmed, bool):
            raise ContractError("source_rights_confirmed must be boolean")
        # Prevent post-validation modification of a candidate market quote.
        object.__setattr__(self, "prices", MappingProxyType(dict(self.prices)))

    @property
    def overround(self) -> Decimal:
        return sum((Decimal(1) / self.prices[k] for k in OUTCOMES), Decimal(0))

    def no_vig_probabilities(self) -> dict[str, Decimal]:
        overround = self.overround
        return {k: (Decimal(1) / self.prices[k]) / overround for k in OUTCOMES}


def expected_return_per_unit(*, quote: ThreeWayQuote, selection: str,
                             forecast_probability: Decimal, cost_fraction: Decimal = Decimal("0")) -> Decimal:
    if selection not in OUTCOMES:
        raise ContractError("selection outside offered three-way market")
    p = money(forecast_probability, nonnegative=True)
    cost = money(cost_fraction, nonnegative=True)
    if p > 1 or cost > 1:
        raise ContractError("probability/cost fraction outside [0,1]")
    return p * quote.prices[selection] - Decimal(1) - cost
