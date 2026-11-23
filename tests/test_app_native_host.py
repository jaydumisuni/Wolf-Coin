"""Actual signed native-child bridge lifecycle across process restart.

No browser or financial account is opened. The fixture represents the
frontend/native host sending normalized observations to a packaged backend.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys

from wolf_app.contracts import REQUEST_SCHEMA


def _sign(request,key):
    raw=json.dumps(request,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return json.dumps({**request,"auth_tag":hmac.new(key,raw.encode("utf-8"),hashlib.sha256).hexdigest()})


def _req(i,operation,payload):
    return {"schema":REQUEST_SCHEMA,"request_id":i,"operation":operation,"payload":payload}


def _run(db,key,requests):
    cmd=[sys.executable,"-m","wolf_app.bridge","--db",str(db),
         "--key-file",str(key)]
    lines=[_sign(x,key.read_bytes()) for x in requests]
    completed=subprocess.run(cmd,input="\n".join(lines)+"\n",
            capture_output=True,text=True,timeout=15,
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])})
    assert completed.returncode==0,completed.stderr
    responses=[json.loads(line) for line in completed.stdout.splitlines()]
    assert len(responses)==len(requests)
    assert all(x["schema"]=="wolf.app.bridge.v1" for x in responses)
    assert all(not x["live_enabled"] and not x["financial_execution_authorized"] for x in responses)
    return responses


def test_full_two_domain_native_host_ipc_restart_recovery(tmp_path):
    from datetime import datetime,timezone,timedelta
    db=tmp_path/"application.sqlite3"
    key=tmp_path/"key.bin"
    setup=subprocess.run([sys.executable,"-m","wolf_app.bridge","--init-key",str(key)],
          capture_output=True,text=True,timeout=10,
          cwd=Path(__file__).resolve().parents[1],
          env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])})
    assert setup.returncode==0,setup.stderr

    def now(shift=0):
        return (datetime.now(timezone.utc)+timedelta(seconds=shift)).isoformat()

    first=[
        _req("start1","host.startup",{"host_instance_id":"one"}),
        _req("sports_reg","account.register",{
            "domain":"sports","account_id":"sports_1","platform_id":"sports_site",
            "currency":"ZMW","display_name":"Sports"}),
        _req("trade_reg","account.register",{
            "domain":"trading","account_id":"trade_1","platform_id":"broker_site",
            "currency":"USD","display_name":"Trading"}),
        _req("sport_login","session.record",{
            "domain":"sports","account_id":"sports_1","state":"ACTIVE",
            "session_ref":"sports_native_tab","observed_at":now(2),
            "device_id":"ATHENA"}),
        _req("trade_login","session.record",{
            "domain":"trading","account_id":"trade_1","state":"ACTIVE",
            "session_ref":"trading_native_tab","observed_at":now(2),
            "device_id":"ATHENA"}),
        _req("sport_obs","observation.ingest",{
            "domain":"sports","account_id":"sports_1","observation_id":"obs_s",
            "session_ref":"sports_native_tab","observed_at":now(3),
            "source":"DOM","origin":"example.invalid",
            "evidence_sha256":"a"*64,
            "fields":{"cash_balance":"100.00","available_balance":"80.00",
                      "pending_bets":"15.00","realized_pnl":"-3.00"}}),
        _req("trade_obs","observation.ingest",{
            "domain":"trading","account_id":"trade_1","observation_id":"obs_t",
            "session_ref":"trading_native_tab","observed_at":now(3),
            "source":"VISIBLE_NETWORK","origin":"broker.invalid",
            "evidence_sha256":"b"*64,
            "fields":{"cash_balance":"400.00","available_balance":"370.00",
                      "unrealized_pnl":"7.00","realized_pnl":"-10.00"}}),
        _req("overview","financial.overview",{}),
    ]
    results=_run(db,key,first)
    assert all(x["status"]=="OK" for x in results)
    overview=results[-1]["data"]
    assert overview["currency_totals"]["ZMW"]["available_balance"]=="80.00"
    assert overview["currency_totals"]["USD"]["available_balance"]=="370.00"
    assert not overview["settled_funds_verified"]

    reboot=[
       _req("restart2","host.startup",{"host_instance_id":"two"}),
       _req("after_reboot","accounts.list",{}),
       _req("check_totals","financial.overview",{}),
    ]
    restarted=_run(db,key,reboot)
    assert restarted[0]["data"]["sessions_requiring_revalidation"]==2
    accounts=restarted[1]["data"]["accounts"]
    assert len(accounts)==2
    assert all(x["session_state"]=="PAUSED" for x in accounts)
    assert all(x["freshness"]=="STALE_LAST_KNOWN" for x in accounts)
    assert restarted[-1]["data"]["currency_totals"]=={}
    assert _run(db,key,[_req("audit","activity.list",{})])[0]["data"]["hash_chain_checked"]
    assert db.is_file()
    if os.name=="posix":
        assert db.stat().st_mode & 0o777 == 0o600
