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
from wolf_funding.cli import describe as funding_status


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
<a class="{'selected' if domain is Domain.TRADING else ''}" href="/trading">Trading</a>
<a href="/lab">Strategy Lab</a><a href="/forecast">Forecast CPU</a><a href="/neural">Neural</a>
<a href="/funding">Funding readiness</a></nav>
<section class="grid"><div class="card"><p>Virtual balance</p><div class="value">{value('balance')}</div><small>Not real ZMW, deposits or winnings</small></div>
<div class="card"><p>Virtual available</p><div class="value">{value('available')}</div><small>Committed exposure is excluded</small></div></section>
<div class="card"><p>Account state</p><div class="value">{value('status')}</div><p>Reserved: {value('reserved')} · Ledger sequence: {value('seq')}</p></div>
<div class="card"><p>Operating authority</p><p>Local research/paper view only. No bookmaker, broker, order entry, funding, automation or qualified predictive strategy.</p>
<p class="subtle">Ledger: <code>{escape(str(database))}</code></p></div>
<footer>Wolf-Coin first light · refreshes every 30 seconds · no external requests</footer>
</main></body></html>''').encode('utf-8')



def funding_page() -> bytes:
    """Strictly informational; never creates a funding rail or approval."""
    sports=funding_status(Domain.SPORTS)
    trading=funding_status(Domain.TRADING)
    def item(data):
        name=escape(data["domain"].title())
        return (f'<div class="card"><h2>{name} pilot</h2>'
                f'<p>Illustrative budget: {escape(data["pilot_budget_ZMW"])} ZMW</p>'
                f'<p>Current approved deposit: {escape(data["max_customer_deposit_authorized_ZMW"])} ZMW</p>'
                f'<p>Maximum modelled action risk: {escape(data["notional_risk_per_action_cap_ZMW"])} ZMW</p>'
                f'<p><strong>FUNDING BLOCKED</strong> — no verified provider or independent release</p></div>')
    return (f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Wolf-Coin · Funding Readiness</title><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30"><style>{STYLE}</style></head>
<body><main><header><div><p>WOLF-COIN · FUNDING GATE</p><h1>Funding readiness</h1>
<span class="tag">NO DEPOSIT / WITHDRAWAL ACCESS</span></div>
<span class="tag">Independent release required</span></header>
<nav><a href="/sports">Sports</a><a href="/trading">Trading</a>
<a href="/forecast">Forecast CPU</a><a href="/neural">Neural</a><a class="selected" href="/funding">Funding readiness</a></nav>
<section class="grid">{item(sports)}{item(trading)}</section>
<div class="card"><h2>Current blockers</h2>
<p>No selected and permitted automated sportsbook; no verified broker/demo account;
no KYC-linked balance readback; no verified funding rail, fees or FX evidence;
no sustained positive-EV/recovery qualification; no approved real-money release.</p>
<p>Mechanical source tests do not grant access to customer funds. Any live execution
is disabled independently of this page.</p></div>
<footer>Local-only status · No payment, order, deposit, credential or external request endpoints</footer>
</main></body></html>''').encode("utf-8")


def lab_page(reports: tuple[Path, Path] | None) -> bytes:
    """One optional local-only research view, never execution authority."""
    if reports is None:
        earlier, subsequent = None, None
    else:
        def read_one(path: Path, expected: str) -> dict | None:
            try:
                # The operator supplies fixed report paths at service startup.
                # Never resolve arbitrary paths from request parameters.
                resolved = path.expanduser().resolve(strict=True)
                if not resolved.is_file() or resolved.stat().st_size > 350_000:
                    return None
                data = json.loads(resolved.read_text(encoding='utf-8'))
                if not isinstance(data, dict) or data.get('schema') != expected:
                    return None
                return data
            except (OSError, ValueError, TypeError, UnicodeError):
                return None
        earlier=read_one(reports[0], 'wolf.historical-odds-replay.v1')
        subsequent=read_one(reports[1], 'wolf.walk-forward-three-window.v1')
    def text(value: object) -> str:
        return escape(str(value), quote=True)
    if earlier is None:
        first='<div class="card"><p>First historical strategy: no verified local result loaded.</p></div>'
    else:
        first=(f'<div class="card"><h2>First strategy — 2024/25 historical test</h2>'
               f'<p>Virtual K{text(earlier.get("starting_virtual_ZMW"))} → '
               f'K{text(earlier.get("ending_virtual_ZMW"))}</p>'
               f'<div class="value">Net K{text(earlier.get("net_virtual_ZMW"))}</div>'
               f'<p>{text(earlier.get("bets"))} historical paper selections · '
               f'ROI on wagers {text(earlier.get("roi_on_wagers_percent"))}%</p>'
               f'<p>Model Brier {text(earlier.get("model_brier"))} · '
               f'Market baseline {text(earlier.get("market_no_vig_brier"))}</p>'
               f'<span class="tag">NOT PROFITABLE / NOT RELEASED</span></div>')
    if subsequent is None:
        second='<div class="card"><p>Walk-forward evaluation: no verified local result loaded.</p></div>'
    else:
        x=subsequent.get('final',{})
        if not isinstance(x,dict):
            x={}
        second=(f'<div class="card"><h2>Three-window qualification — 2025/26</h2>'
                f'<p>Validation decision: <strong>{text(subsequent.get("decision"))}</strong></p>'
                f'<div class="value">{text(x.get("bets"))} admitted historical paper bets</div>'
                f'<p>Ending virtual K{text(x.get("final_virtual_ZMW"))} · '
                f'Net K{text(x.get("net_virtual_ZMW"))}</p>'
                f'<p>Final model/market Brier: {text(x.get("candidate_brier"))} / '
                f'{text(x.get("market_brier"))}</p>'
                f'<span class="tag">NO VALIDATED PREDICTION EDGE · NO LIVE EXECUTION</span></div>')
    return (f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Wolf-Coin · Strategy Lab</title><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60"><style>{STYLE}</style></head>
<body><main><header><div><p>WOLF-COIN · EVIDENCE LAB</p><h1>Strategy results</h1>
<span class="tag">PRIVATE HISTORICAL RESEARCH · NO LIVE FUNDS</span></div></header>
<nav><a href="/sports">Sports</a><a href="/trading">Trading</a>
<a class="selected" href="/lab">Strategy Lab</a><a href="/forecast">Forecast CPU</a><a href="/neural">Neural</a>
<a href="/funding">Funding readiness</a></nav>
<section class="grid">{first}{second}</section>
<div class="card"><h2>Engineering verdict</h2>
<p>A successful test suite proves deterministic software behavior, not a profitable strategy.
The tested football strategy lost virtual funds; a later out-of-sample qualification rejected
all candidate models. No automatic learning, deposits, account authentication or orders are active.</p>
<p>Historical bookmaker opening odds do not prove those prices were available to this account.</p></div>
<footer>Read-only local report · independent release still required · no external browser requests</footer>
</main></body></html>""").encode('utf-8')



def forecast_page(report_path: Path | None) -> bytes:
    """Local static view of one pinned CPU comparison, no model runtime."""
    data = None
    if report_path is not None:
        try:
            path = report_path.expanduser().resolve(strict=True)
            if path.is_file() and 0 < path.stat().st_size <= 30_000:
                source = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(source, dict) and source.get("schema") == "wolf.lagged-features-market-cpu.v1":
                    data = source
        except (OSError,UnicodeError,TypeError,ValueError):
            pass
    def e(value):
        return escape(str(value),quote=True)
    if data is None:
        panel='<div class="card"><p>Source-bound CPU comparison unavailable.</p></div>'
    else:
        market=data.get("market_validation_scores",{})
        candidates=data.get("candidate_validation_scores",[])
        if not isinstance(candidates,list):
            candidates=[]
        candidates=[x for x in candidates if isinstance(x,dict)
                    and isinstance(x.get("brier"),(int,float))]
        chosen=min(candidates,key=lambda x:x["brier"]) if candidates else {}
        decision=data.get("decision","RESEARCH_NOT_QUALIFIED")
        panel=(f'<div class="card"><h2>Market-relative CPU forecast</h2>'
               f'<p>Prior-date team form and recorded bookmaker odds only.</p>'
               f'<p>{e(data.get("training_rows"))} training · {e(data.get("validation_rows"))} validation '
               f'· {e(data.get("exposed_diagnostic_rows"))} exposed diagnostic fixtures</p>'
               f'<section class="grid">'
               f'<div><small>Bookmaker market Brier</small><div class="value">{e(market.get("brier"))}</div></div>'
               f'<div><small>Best CPU candidate Brier</small><div class="value">{e(chosen.get("brier"))}</div></div>'
               f'</section><p>Market log-loss {e(market.get("log_loss"))}; '
               f'candidate {e(chosen.get("log_loss"))}</p>'
               f'<p><strong>Decision: {e(decision)}</strong></p>'
               f'<p>Source truth qualified: {e(data.get("source_truth_qualified"))}; '
               f'new untouched period included: {e(data.get("final_unexamined_period_included"))}</p>'
               f'<small>Derived feature SHA-256: {e(data.get("feature_sha256"))}</small>'
               f'</div>')
    return (f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Wolf-Coin · CPU Research</title><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60"><style>{STYLE}</style></head>
<body><main><header><div><p>WOLF-COIN · SUP RESEARCH</p><h1>CPU forecasting comparison</h1>
<span class="tag">UNQUALIFIED RESEARCH · NO MONEY EXECUTION</span></div></header>
<nav><a href="/sports">Sports</a><a href="/trading">Trading</a>
<a href="/lab">Strategy Lab</a><a class="selected" href="/forecast">Forecast CPU</a><a href="/neural">Neural</a>
<a href="/funding">Funding readiness</a></nav>{panel}
<div class="card"><h2>Independent qualification</h2>
<p>The SUP Director requires a source-qualified learning package. Its
current status is AWAIT_SOURCE_QUALIFICATION. SUP-Bit's resource planner
measured host fit for a declared small CPU workload, not neural training quality.</p>
<p>No model has demonstrated a positive financial edge. The exposed
2025/26 season cannot be treated as a new untouched holdout.</p></div>
<footer>Read-only local evidence; no external provider, trainer or funding access</footer>
</main></body></html>""").encode("utf-8")




def neural_page(report_path: Path | None) -> bytes:
    """Static CC0 experiment evidence. Never loads model weights or train data."""
    data=None
    if report_path is not None:
        try:
            path=report_path.expanduser().resolve(strict=True)
            if path.is_file() and 0 < path.stat().st_size < 16_000:
                value=json.loads(path.read_text(encoding="utf-8"))
                if (isinstance(value,dict) and value.get("schema")=="wolf.cc0-neural-public-summary.v1"
                    and value.get("live_enabled") is False and value.get("financial_edge_proven") is False):
                    data=value
        except (OSError,ValueError,UnicodeError,TypeError):
            pass
    def e(value):
        return escape(str(value),quote=True)
    if data is None:
        content='<div class="card"><p>CC0 neural research evidence unavailable.</p></div>'
    else:
        lohi=data.get("holdout_brier_gain_interval",[])
        if not isinstance(lohi,list) or len(lohi)!=2:
            lohi=["?", "?"]
        # Optional additional source-bound research proof. These are advisory
        # statuses only and never authorize a model, venue or capital action.
        route=''
        if (data.get("typed_route_training")=="PRODUCT_OWNED_CPU_TRAINING_REPRODUCED"
            and data.get("typed_route_verifier")=="NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY"
            and data.get("typed_route_sup_admitted") is False
            and data.get("typed_route_formula_certificate") is False):
            route=(f'<div class="card"><h2>Typed CPU research route</h2>'
                   f'<p>Frozen 2,660-match training and 380-match validation '
                   f'<strong>reproduced exactly</strong>.</p>'
                   f'<p>{e(data.get("typed_route_prediction_rows"))} predictions independently '
                   f'checked without the training runtime.</p>'
                   f'<p>Maximum absolute probability difference: '
                   f'{e(data.get("typed_route_max_absolute_error"))}</p>'
                   f'<span class="tag">WOLF-COIN-OWNED CANDIDATE · NOT ADMITTED BY SUP OR FORMULA</span></div>')
        content=(f'<section class="grid">'
                 f'<div class="card"><p>Training matches</p><div class="value">{e(data.get("training_rows"))}</div></div>'
                 f'<div class="card"><p>Validation matches</p><div class="value">{e(data.get("validation_rows"))}</div></div>'
                 f'<div class="card"><p>2026/27 completed</p><div class="value">{e(data.get("holdout_scored_matches"))}</div>'
                 f'<small>{e(data.get("holdout_unscored_matches"))} still unscored in pinned archive</small></div>'
                 f'</section>'
                 f'<div class="card"><h2>Validation: historical-frequency vs MLP</h2>'
                 f'<p>Frequency baseline Brier {e(data.get("validation_class_prior_brier"))} · '
                 f'linear {e(data.get("validation_linear_brier"))} · '
                 f'MLP {e(data.get("validation_neural_brier"))}</p></div>'
                 f'<div class="card"><h2>Fresh, but partial, 2026/27 evaluation</h2>'
                 f'<p>Frequency baseline Brier {e(data.get("holdout_class_prior_brier"))} · '
                 f'MLP {e(data.get("holdout_neural_brier"))}</p>'
                 f'<p>95% match-day bootstrap gain interval: {e(lohi[0])} to {e(lohi[1])}.</p>'
                 f'<span class="tag">INTERVAL CROSSES ZERO · NO PROVEN ADVANTAGE</span></div>'
                 f'<div class="card"><h2>SUP research handoff</h2>'
                 f'<p>Director: <strong>{e(data.get("sup_director_stage"))}</strong></p>'
                 f'<p>{e(data.get("historical_score_crosscheck_count"))} externally cross-checked scores; '
                 f'{e(data.get("historical_score_crosscheck_conflicts"))} discrepancies.</p>'
                 f'<small>Frozen model {e(data.get("model_frozen_digest"))}</small></div>'
                 +route)
    return (f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wolf-Coin · CC0 Neural Lab</title><meta http-equiv="refresh" content="60">
<style>{STYLE}</style></head>
<body><main><header><div><p>WOLF-COIN · CC0 NEURAL LAB</p><h1>Neural forecasting proof</h1>
<span class="tag">RESEARCH ONLY · NO SUP TRAINING LEASE · NO FUNDS</span></div></header>
<nav><a href="/sports">Sports</a><a href="/trading">Trading</a>
<a href="/lab">Strategy Lab</a><a href="/forecast">Forecast CPU</a>
<a class="selected" href="/neural">Neural</a><a href="/funding">Funding readiness</a></nav>
{content}
<div class="card"><h2>Engineering boundary</h2>
<p>Public-domain CC0 results only for neural training. The restricted historical
bookmaker archive was used for a separate private outcome audit only. The source
snapshot has 45 completed 2026/27 matches, latest through September 20.
SUP-Bit has NOT trained this MLP. No bookmaker edge or future profit is proven.</p></div>
<footer>Source-pinned local proof · only static evidence, no external requests</footer>
</main></body></html>""").encode("utf-8")



def handler(db: Path, account_id: str, *, lab_reports: tuple[Path, Path] | None = None,
            forecast_report: Path | None = None,
            neural_report: Path | None = None):
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
            if path == '/lab':
                return self._send(200,lab_page(lab_reports),'text/html; charset=utf-8')
            if path == '/forecast':
                return self._send(200,forecast_page(forecast_report),'text/html; charset=utf-8')
            if path == '/neural':
                return self._send(200,neural_page(neural_report),'text/html; charset=utf-8')
            if path == '/funding':
                return self._send(200,funding_page(),'text/html; charset=utf-8')
            if path == '/api/funding-readiness':
                return self._send(200,json.dumps({
                    "sports":funding_status(Domain.SPORTS),
                    "trading":funding_status(Domain.TRADING),
                },sort_keys=True).encode(),'application/json; charset=utf-8')
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
