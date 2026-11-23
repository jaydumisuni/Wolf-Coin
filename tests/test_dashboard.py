from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen, Request
from urllib.error import HTTPError

from wolf_core.paper_operator import run
from wolf_gateway.dashboard import handler, account_report
from wolf_core.contracts import Domain


def test_read_only_two_dashboard_paths_and_headers(tmp_path: Path):
    db=tmp_path/'paper.db'
    assert run(['--db',str(db),'--domain','sports','--account','demo','init']) == 0
    assert run(['--db',str(db),'--domain','trading','--account','demo','init']) == 0
    assert run(['--db',str(db),'--domain','sports','--account','demo','deposit','--amount','100','--event-id','deposit']) == 0
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(db,'demo'))
    th=Thread(target=server.serve_forever, daemon=True);th.start()
    try:
        url=f'http://127.0.0.1:{server.server_port}'
        for path,title,balance in [('/sports',b'Sports paper account',b'100'),('/trading',b'Trading paper account',b'>0<')]:
            with urlopen(url+path,timeout=3) as response:
                body=response.read()
                assert title in body and balance in body
                assert b'NO LIVE EXECUTION' in body
                assert response.headers['Cache-Control']=='no-store'
        with urlopen(url+'/health',timeout=3) as response:
            payload=response.read()
            assert b'"live_enabled": false' in payload
        try:
            urlopen(Request(url+'/sports',method='POST'),timeout=3)
        except HTTPError as exc:
            assert exc.code==405
        else: raise AssertionError('POST unexpectedly allowed')
    finally:
        server.shutdown();server.server_close();th.join(timeout=4)


def test_missing_paper_data_reports_unavailable_without_creating_db(tmp_path):
    db=tmp_path/'nonexistent.db'
    assert account_report(db,Domain.SPORTS,'demo')['status']=='UNAVAILABLE'
    assert not db.exists()
