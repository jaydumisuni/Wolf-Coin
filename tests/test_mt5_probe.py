from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace as Row

import pytest

from wolf_markets.mt5_probe import MT5InspectionBlocked, inspect_demo


class MockMT5:
    def __init__(self):
        self.login = 123456
        self.server = "Demo-Server"
        self.currency = "USD"
        self.trade_mode = 0
        self.connected = True
        self.ready = True
        self.has_account = True
        self.has_positions = True
        self.shutdown_calls = 0
        self.initialize_calls = 0
        self.order_send_calls = 0

    def initialize(self):
        self.initialize_calls += 1
        return self.ready

    def shutdown(self):
        self.shutdown_calls += 1

    def terminal_info(self):
        return Row(connected=self.connected)

    def account_info(self):
        if not self.has_account:
            return None
        return Row(login=self.login, server=self.server,
                   currency=self.currency, trade_mode=self.trade_mode,
                   balance=100.0, equity=98.75)

    def orders_get(self):
        return ()

    def positions_get(self):
        return (Row(ticket=12),) if self.has_positions else None

    def order_send(self, *args, **kwargs):
        self.order_send_calls += 1
        raise AssertionError("read-only probe must never call order_send")

    def order_check(self, *args, **kwargs):
        raise AssertionError("read-only probe must never call order_check")

    def login(self, *args, **kwargs):
        raise AssertionError("read-only probe must never call login")


def probe(api: MockMT5):
    return inspect_demo(api, expected_login=123456, expected_server="Demo-Server",
                        expected_currency="USD")


def test_demo_account_inspection_returns_read_only_data():
    mt=MockMT5()
    x=probe(mt)
    assert x.login==123456 and x.currency=="USD"
    assert x.orders==0 and x.positions==1
    assert x.balance==Decimal("100.0") and x.equity==Decimal("98.75")
    assert x.connected and x.live_effects_enabled is False
    assert mt.shutdown_calls==1 and mt.initialize_calls==1 and mt.order_send_calls==0


@pytest.mark.parametrize("attr,value,reason",[
    ("login",1,"identity mismatch"),
    ("server","Other","identity mismatch"),
    ("currency","EUR","identity mismatch"),
    ("trade_mode",2,"DEMO"),
    ("trade_mode",1,"DEMO"),
    ("connected",False,"disconnected"),
    ("has_account",False,"readback unavailable"),
    ("has_positions",False,"readback unavailable"),
    ("ready",False,"initialization unavailable"),
])
def test_negative_broker_conditions_never_triggers_an_order(attr,value,reason):
    m=MockMT5()
    setattr(m,attr,value)
    with pytest.raises(MT5InspectionBlocked,match=reason):
        probe(m)
    assert m.order_send_calls==0
    assert m.shutdown_calls==1


@pytest.mark.parametrize("login,server,currency",[
    (None,"Demo-Server","USD"),
    (0,"Demo-Server","USD"),
    (123456,"","USD"),
    (123456,"Demo-Server","usd"),
])
def test_identity_inputs_fail_before_terminal_connection(login,server,currency):
    m=MockMT5()
    with pytest.raises(MT5InspectionBlocked):
        inspect_demo(m,expected_login=login,expected_server=server,expected_currency=currency)
    assert m.initialize_calls==0
    assert m.order_send_calls==0
