"""Loopback-only, read-only browser dashboards for separate virtual accounts.

No financial API, remote bind, POST endpoint, credential, strategy executor,
JavaScript order placement, account write or external network connection exists.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from wolf_core.bankroll import PaperBankroll
from wolf_core.cli import doctor
from wolf_core.contracts import AccountScope, ContractError, Domain, identifier
from wolf_core.ledger import EventLedger


STYLE = """
:root {color-scheme:dark;font-family:system-ui,Segoe UI,sans-serif;background:#090e1a;color:#f0f5ff}
*{box-sizing:border-box}body{margin:0;padding:5vh 5vw;background:radial-gradient(circle at 85% -10%,#232957,#090e1a 62%);min-height:100vh}
main{max-width:980px;margin:auto}header{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
h1{font-size:2.1rem;letter-spacing:-.04em;margin:.15em 0}p,.subtle{color:#a5b2ce}
nav{display:flex;gap:10px;margin:26px 0}a{color:#c9dcff;text-decoration:none;padding:10px 17px;border:1px solid #465274;border-radius:11px}
a.selected{background:#334b96;border-color:#8bafff;color:white}
.card{background:#1a2133cc;border:1px solid #35425c;border-radius:18px;padding:26px;margin:18px 0;box-shadow:0 20px 55px #03050e44}
.value{font-size:2.5rem;font-weight:650;letter-spacing:-.06em;margin:8px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.tag{font:600 .78rem system-ui;padding:7px 10px;border:1px solid #66718e;border-radius:50px;display:inline-block}
small{color:#8c9bb9}footer{margin:36px 0;color:#b7c2d7}code{color:#a4bbff;word-break:break-word}
"""


def account_report(db_path: Path, domain: Domain, account_id: str) -> dict:
    """Derive from native hash-checked events; never invent a balance."""
    report = doctor(db_path)
    if report['status'] != 'RESEARCH_ONLY':
        return {'status':'UNAVAILABLE','reason':report.get('reason',report['status']), 'balance':None}
    try:
        state = PaperBankroll(EventLedger(db_path)).state(AccountScope(domain, account_id))
        return {'status':state.status,'balance':str(state.balance),'available':str(state.available),
                'reserved':str(state.balance-state.available),'seq':state.seq}
    except (ContractError, OSError, ValueError) as exc:
        return {'status':'UNAVAILABLE','reason':type(exc).__name__,'balance':None}


def page(domain: Domain, report: dict, database: Path) -> bytes:
    name = 'Sports' if domain is Domain.SPORTS else 'Trading'
    def value(key, default='Unavailable'):
        raw=report.get(key)
        return escape(str(raw if raw is not None else default))
    return (f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Wolf-Coin · {name} Paper</title><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30"><style>{STYLE}</style></head>
<body><main><header><div><p>WOLF-COIN · RESEARCH CONSOLE</p><h1>{name} paper account</h1>
<span class="tag">NO LIVE EXECUTION</span></div><span class="tag">Manual / virtual funds</span></header>
<nav><a class="{'selected' if domain is Domain.SPORTS else ''}" href="/sports">Sports</a>
<a class="{'selected' if domain is Domain.TRADING else ''}" href="/trading">Trading</a></nav>
<section class="grid"><div class="card"><p>Virtual balance</p><div class="value">{value('balance')}</div><small>Not real ZMW, deposits or winnings</small></div>
<div class="card"><p>Virtual available</p><div class="value">{value('available')}</div><small>Committed exposure is excluded</small></div></section>
<div class="card"><p>Account state</p><div class="value">{value('status')}</div><p>Reserved: {value('reserved')} · Ledger sequence: {value('seq')}</p></div>
<div class="card"><p>Operating authority</p><p>Local research/paper view only. No bookmaker, broker, order entry, funding, automation or qualified predictive strategy.</p>
<p class="subtle">Ledger: <code>{escape(str(database))}</code></p></div>
<footer>Wolf-Coin first light · refreshes every 30 seconds · no external requests</footer>
</main></body></html>''').encode('utf-8')


def handler(db: Path, account_id: str):
    class DashboardHandler(BaseHTTPRequestHandler):
        def _send(self, code: int, data: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self) -> None:
            path=urlsplit(self.path).path
            if path == '/health':
                data=json.dumps({'mode':'PAPER','live_enabled':False,'remote_enabled':False,'ledger':doctor(db)['status']}).encode()
                return self._send(200,data,'application/json; charset=utf-8')
            if path == '/':
                self.send_response(302);self.send_header('Location','/sports');self.end_headers();return
            if path not in ('/sports','/trading'):
                return self._send(404,b'not found','text/plain; charset=utf-8')
            domain=Domain(path[1:])
            data=page(domain,account_report(db,domain,account_id),db)
            return self._send(200,data,'text/html; charset=utf-8')
        def do_POST(self) -> None:
            return self._send(405,b'read-only','text/plain; charset=utf-8')
        def log_message(self,*args) -> None:
            pass
    return DashboardHandler


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(prog='wolf-dashboard',description='Loopback-only paper viewer')
    parser.add_argument('--db',required=True,type=Path)
    parser.add_argument('--account',default='pilot-1')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args(argv)
    identifier(args.account)
    if not 1024 <= args.port <= 65535:
        parser.error('port must be in [1024, 65535]')
    # Fixed address is an intentional security boundary. No --host option.
    with ThreadingHTTPServer(('127.0.0.1',args.port),handler(args.db,args.account)) as server:
        print(f'Wolf-Coin paper viewer: http://127.0.0.1:{args.port}/sports and /trading',flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
