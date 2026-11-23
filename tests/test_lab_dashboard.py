from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

from wolf_core.paper_operator import run
from wolf_gateway.dashboard import handler, lab_page


def test_lab_view_uses_explicit_local_reports_never_executes(tmp_path):
    db=tmp_path/"paper.db"
    assert run(["--db",str(db),"--domain","sports","--account","pilot","init"])==0
    assert run(["--db",str(db),"--domain","trading","--account","pilot","init"])==0
    initial=tmp_path/"initial.json"
    initial.write_text(json.dumps({
        "schema":"wolf.historical-odds-replay.v1",
        "starting_virtual_ZMW":"100","ending_virtual_ZMW":"78.609474",
        "net_virtual_ZMW":"-21.390526","bets":102,
        "roi_on_wagers_percent":"-48.23",
        "model_brier":0.607806,"market_no_vig_brier":0.578664,
    }))
    later=tmp_path/"later.json"
    later.write_text(json.dumps({
        "schema":"wolf.walk-forward-three-window.v1",
        "decision":"ABSTAIN_NO_VALIDATED_FORECAST_EDGE",
        "final":{"bets":0,"final_virtual_ZMW":"100.000000",
                 "net_virtual_ZMW":"0.000000","candidate_brier":0.611512,
                 "market_brier":0.611512}
    }))
    server=ThreadingHTTPServer(("127.0.0.1",0),handler(db,"pilot",lab_reports=(initial,later)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        root=f"http://127.0.0.1:{server.server_port}"
        with urlopen(root+"/lab",timeout=3) as res:
            text=res.read().decode()
            assert "78.609474" in text and "-21.390526" in text
            assert "ABSTAIN_NO_VALIDATED_FORECAST_EDGE" in text
            assert "NO LIVE FUNDS" in text
            assert res.headers["Content-Security-Policy"].startswith("default-src 'none'")
        with urlopen(root+"/sports",timeout=3) as res:
            assert "Strategy Lab" in res.read().decode()
        with pytest.raises(HTTPError) as e:
            urlopen(Request(root+"/lab",method="POST"),timeout=3)
        assert e.value.code==405
        with pytest.raises(HTTPError) as e:
            urlopen(root+"/lab/exploit",timeout=3)
        assert e.value.code==404
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)


def test_lab_view_escapes_any_report_content(tmp_path):
    p=tmp_path/"first.json"
    q=tmp_path/"later.json"
    p.write_text(json.dumps({"schema":"wolf.historical-odds-replay.v1",
                             "net_virtual_ZMW":"<script>alert(1)</script>"}))
    q.write_text(json.dumps({"schema":"wolf.walk-forward-three-window.v1",
                             "decision":"<img src=x onerror=alert(1)>","final":{}}))
    response=lab_page((p,q)).decode()
    assert "<script>alert(1)</script>" not in response
    assert "<img src=x" not in response
    assert "&lt;script&gt;" in response
    assert "&lt;img" in response


def test_lab_view_missing_report_is_still_safe(tmp_path):
    first=tmp_path/"missing.json"
    second=tmp_path/"missing2.json"
    response=lab_page((first,second)).decode()
    assert "no verified local result loaded" in response
    assert "NO LIVE FUNDS" in response


def test_report_path_does_not_come_from_request(tmp_path):
    bad=tmp_path/"bad.json"
    bad.write_text(json.dumps({"schema":"wolf.unknown.v0","secrets":"must-not-display"}))
    r=lab_page((bad,bad)).decode()
    assert "must-not-display" not in r
