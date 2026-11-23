"""Source-bound SUP CPU forecasting report is local-only and read-only."""
from __future__ import annotations
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

from wolf_core.paper_operator import run
from wolf_gateway.dashboard import handler, forecast_page


def report():
    return {
        "schema":"wolf.lagged-features-market-cpu.v1",
        "training_rows":760,"validation_rows":380,"exposed_diagnostic_rows":380,
        "market_validation_scores":{"brier":0.578663803,"log_loss":0.970757673},
        "candidate_validation_scores":[
            {"l2":0.02,"brier":0.583930334,"log_loss":0.978564729},
            {"l2":0.1,"brier":0.582436879,"log_loss":0.976451876},
            {"l2":0.5,"brier":0.580325109,"log_loss":0.973309196}
        ],
        "decision":"ABSTAIN_NO_VALIDATED_FORECAST_EDGE",
        "source_truth_qualified":False,"final_unexamined_period_included":False,
        "feature_sha256":"900a45ead9feb37b85450bda63ebcb45e386eb308f5593d66047548af59e87f6"
    }


def test_forecast_page_shows_verified_rejection(tmp_path):
    p=tmp_path/"proof.json";p.write_text(json.dumps(report()))
    html=forecast_page(p).decode()
    assert "0.578663803" in html and "0.580325109" in html
    assert "AWAIT_SOURCE_QUALIFICATION" in html
    assert "ABSTAIN_NO_VALIDATED_FORECAST_EDGE" in html
    assert "NO MONEY EXECUTION" in html


def test_forecast_view_does_not_load_untrusted_shape(tmp_path):
    p=tmp_path/"unexpected.json"
    p.write_text(json.dumps({"schema":"unknown","secret":"do-not-show"}))
    assert "do-not-show" not in forecast_page(p).decode()
    assert "unavailable" in forecast_page(p).decode()


def test_forecast_view_escapes_report_strings(tmp_path):
    p=tmp_path/"unsafe.json"
    x=report()
    x["decision"]="<img src=x onerror=alert(1)>"
    p.write_text(json.dumps(x))
    html=forecast_page(p).decode()
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_http_forecast_is_read_only_loopback(tmp_path):
    db=tmp_path/"paper.db"
    assert run(["--db",str(db),"init"])==0
    p=tmp_path/"proof.json";p.write_text(json.dumps(report()))
    s=ThreadingHTTPServer(("127.0.0.1",0),handler(db,"pilot-1",forecast_report=p))
    t=Thread(target=s.serve_forever,daemon=True);t.start()
    try:
        base=f"http://127.0.0.1:{s.server_port}"
        with urlopen(base+"/forecast",timeout=3) as r:
            html=r.read().decode()
            assert r.status==200 and "SUP RESEARCH" in html
            assert "0.580325109" in html
            assert r.headers["Content-Security-Policy"].startswith("default-src 'none'")
        with pytest.raises(HTTPError) as e:
            urlopen(Request(base+"/forecast",method="POST"),timeout=3)
        assert e.value.code==405
        with pytest.raises(HTTPError) as e:
            urlopen(base+"/forecast/../secrets",timeout=3)
        assert e.value.code==404
    finally:
        s.shutdown();s.server_close();t.join(timeout=5)

def test_json_array_or_invalid_candidate_shape_fails_closed(tmp_path):
    p=tmp_path/"array.json"
    p.write_text("[]")
    assert "unavailable" in forecast_page(p).decode()
    r=report()
    r["candidate_validation_scores"]=["untrusted",{"brier":0.58}]
    p.write_text(json.dumps(r))
    output=forecast_page(p).decode()
    assert "CPU forecasting comparison" in output
    assert "NO MONEY EXECUTION" in output
