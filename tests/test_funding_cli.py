from __future__ import annotations

import json
import pytest

from wolf_core.contracts import Domain
from wolf_funding.cli import describe, main

@pytest.mark.parametrize("domain,expected",[(Domain.SPORTS,"0.500"),(Domain.TRADING,"0.2500")])
def test_funding_readiness_refuses_money_for_each_domain(domain,expected):
    x=describe(domain)
    assert x["pilot_budget_ZMW"]=="100"
    assert x["notional_risk_per_action_cap_ZMW"]==expected
    assert x["max_customer_deposit_authorized_ZMW"]=="0"
    assert not x["live_mode_allowed"]
    assert not x["funding_permitted"]
    assert x["transfer_adapters"]==0
    assert "provider-automation-permission-unknown" in x["external_blockers"]

def test_cannot_approve_funds_by_merely_giving_provider_name():
    x=describe(Domain.TRADING,name="some-api")
    assert x["candidate_provider"]=="some-api"
    assert not x["funding_permitted"]
    assert not x["provider_connected"]

@pytest.mark.parametrize("domain",("sports","trading"))
def test_funding_cli_outputs_machine_readable_fail_closed_status(capsys,domain):
    assert main(["--domain",domain])==0
    x=json.loads(capsys.readouterr().out)
    assert x["failure_mode"]=="FAIL_CLOSED"
    assert x["max_customer_deposit_authorized_ZMW"]=="0"
    assert x["total_planned_budget_ZMW"]=="200"
