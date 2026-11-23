"""Five-gate dashboard is sealed, read-only and excludes all live actions."""
from __future__ import annotations

from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json

import pytest

from wolf_core.contracts import Domain
from wolf_core.paper_operator import run
from wolf_execution.five_gate_report import five_gate_report
from wolf_gateway.dashboard import five_gate_page,handler


def reports(tmp_path):
    files=[]
    for domain in (Domain.SPORTS,Domain.TRADING):
        p=tmp_path/(domain.value+"-gate.json")
        p.write_text(json.dumps(five_gate_report({},domain=domain),sort_keys=True))
        files.append(p)
    return tuple(files)


def test_verified_snapshot_shows_both_domain_gate_sets(tmp_path):
    pages=reports(tmp_path)
    html=five_gate_page(pages).decode()
    assert "Sports: 0 / 5 accepted" in html
    assert "Trading: 0 / 5 accepted" in html
    assert html.count("BLOCKED")>=10
    assert "PAPER ONLY" in html and "NO MONEY APPROVED" in html
    assert "No deposits" in html


def test_missing_one_domain_refuses_to_show_misleading_approval(tmp_path):
    sports,_=reports(tmp_path)
    html=five_gate_page((sports,tmp_path/"missing.json")).decode()
    assert "evidence unavailable" in html
    assert "NO MONEY APPROVED" in html


def test_forged_real_money_fields_refused(tmp_path):
    files=reports(tmp_path)
    data=json.loads(files[0].read_text())
    data["real_money_permitted"]=True
    data["completed_real_money_gates"]=5
    files[0].write_text(json.dumps(data))
    html=five_gate_page(files).decode()
    assert "evidence unavailable" in html


def test_cross_site_script_from_untrusted_prose_escaped(tmp_path):
    files=reports(tmp_path)
    data=json.loads(files[0].read_text())
    data["gates"][0]["unmet_requirements"].append("<img src=x onerror=alert(1)>")
    files[0].write_text(json.dumps(data))
    html=five_gate_page(files).decode()
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_end_to_end_local_http_returns_200_and_rejects_post(tmp_path):
    db=tmp_path/"paper.sqlite3"
    assert run(["--db",str(db),"init"])==0
    files=reports(tmp_path)
    server=ThreadingHTTPServer(("127.0.0.1",0),handler(db,"pilot-1",gate_reports=files))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        root=f"http://127.0.0.1:{server.server_port}"
        for path in ("/gates","/sports","/trading","/health"):
            with urlopen(root+path,timeout=4) as response:
                assert response.status==200
                if path=="/gates":
                    html=response.read().decode()
                    assert "Sports: 0 / 5 accepted" in html
                    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
        with pytest.raises(HTTPError) as exc:
            urlopen(Request(root+"/gates",method="POST"),timeout=4)
        assert exc.value.code==405
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
