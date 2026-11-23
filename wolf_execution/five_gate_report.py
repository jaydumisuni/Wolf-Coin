"""Read-only Wolf-Coin five-delivery-gate inventory.

The status command cannot grant, sign, dispatch, enable payment, or connect to
a bookmaker or broker. It distinguishes local mechanical evidence from true
external provider, profitability, independent acceptance and release proofs.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys

from wolf_core.contracts import Domain
from wolf_execution.readiness import observed_tenfold_states,report as tenfold_report


GATES = (
    ("FORMULA_SUP_ROUTE", "Independently admitted tabular neural training route"),
    ("AUTHORIZED_MARKET_FEED", "Licensed, timestamped and executable customer quotes"),
    ("INDEPENDENT_PROFITABILITY", "Positive expected value after actual costs on untouched data"),
    ("AUTONOMOUS_VENUE_EXECUTION", "Demo/live provider order, settlement and restart readback"),
    ("PRODUCTION_RELEASE", "Tenfold, operator, security and owner-signed release"),
)


def five_gate_report(states: dict[str,str] | None, *, domain: Domain,
                     offline_proofs: dict | None=None) -> dict:
    if domain not in (Domain.SPORTS,Domain.TRADING):
        raise ValueError("invalid financial domain")
    proof = offline_proofs or {}
    if not isinstance(proof,dict):
        raise ValueError("invalid offline proof bundle")
    # The following are *status displays*, not grants. An offline file may
    # supply a "paper verified" indicator but can never create legal venue
    # rights, production SUP acceptance or financial authorization.
    sup = proof.get("sup_director_stage")
    route = proof.get("typed_numeric_status")
    quote_kind = proof.get("quote_source_kind")
    paper_cycle = proof.get("paper_cycle_status")
    selection = proof.get("shadow_status")
    existing = tenfold_report(domain,states)
    names = {
        "FORMULA_SUP_ROUTE":{
          "local_evidence":[
             "Product-owned CPU model weights/independent predictions reproduced"
             if route=="NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY" else "No verified typed CPU candidate",
             "SUP Director: "+sup if sup else "SUP Director disposition not bound"
          ],
          "unmet":[
              "An independently accepted Formula mathematical/type qualification",
              "A genuinely admitted SUP tabular method, not a Soup LLM method relabeled"
          ],
        },
        "AUTHORIZED_MARKET_FEED":{
          "local_evidence":[
              "Offline quote-envelope parser available",
              "Captured source category: "+str(quote_kind or "NONE")
          ],
          "unmet":[
              "Specific permitted provider account/API and jurisdiction/terms review",
              "Account-executable odds with verifiable pre-event timestamps and settlement truth",
              "Separate broker market/lot/spread/slippage/fee qualification for trading",
          ] if domain is Domain.TRADING else [
              "Specific permitted sportsbook/exchange and jurisdiction/terms review",
              "Account-executable odds with verifiable pre-event timestamps and settlement truth"
          ],
        },
        "INDEPENDENT_PROFITABILITY":{
          "local_evidence":[
              "Hypothetical price/cost audit: "+str(selection or "NOT RUN"),
              "45-match neural holdout confidence interval includes zero"
          ],
          "unmet":[
              "New complete independent holdout; no reuse of already examined 2026/27 subset",
              "Time-authorized quotes, provider fills, correct customer costs and robust positive after-cost interval"
          ],
        },
        "AUTONOMOUS_VENUE_EXECUTION":{
          "local_evidence":[
              "Internal journal/simulator: "+str(paper_cycle or "NOT RUN"),
              "UNKNOWN after restart never causes automatic resubmission"
          ],
          "unmet":[
              "Authorized provider demo integration and actual server-side order identity",
              "Stop/loss limits, authoritative settlement, reconnect and emergency-halt drill"
          ],
        },
        "PRODUCTION_RELEASE":{
          "local_evidence":[
              "Tenfold independently PROVEN gates: "+
              str(existing["proven_gate_count"])+"/"+str(existing["required_gate_count"]),
              "No owner-signed release or live/funding adapter installed"
          ],
          "unmet":[
              "Independent review and documented owner approval for this domain",
              "All required Tenfold gates and actual provider credentials/account acceptance"
          ],
        },
    }
    records=[]
    for gate,label in GATES:
        records.append({
          "gate":gate, "label":label,
          "engineering_candidate_present":bool(
              (gate=="FORMULA_SUP_ROUTE" and route=="NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY")
              or (gate=="AUTHORIZED_MARKET_FEED" and quote_kind in ("SIMULATED_ONLY","EXTERNAL_UNQUALIFIED"))
              or (gate=="INDEPENDENT_PROFITABILITY" and selection=="HYPOTHETICAL_RESEARCH_NOT_EXECUTABLE")
              or (gate=="AUTONOMOUS_VENUE_EXECUTION" and paper_cycle=="SIMULATION_ONLY_NOT_REAL_EXECUTION")
          ),
          "status":"BLOCKED_INDEPENDENT_ACCEPTANCE",
          "local_evidence":names[gate]["local_evidence"],
          "unmet_requirements":names[gate]["unmet"],
        })
    return {
       "schema":"wolf.five-delivery-gates.v1",
       "domain":domain.value,
       "report_only":True,
       "authority_source":"Tenfold read-only campaign and offline unadmitted research artifacts",
       "gates":records,
       "completed_real_money_gates":0,
       "total_delivery_gates":len(records),
       "tenfold_proven_count":existing["proven_gate_count"],
       "tenfold_required_count":existing["required_gate_count"],
       "real_money_permitted":False,
       "deposit_allowed":False,
       "broker_or_sportsbook_live_exec_available":False,
       "release_suggested":False,
       "status":"NOT_FUNDING_READY",
       "conclusion":"Local engineering advances cannot replace independent strategy, data rights, venue and owner release acceptance."
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="wolf-five-gates")
    p.add_argument("--domain",required=True,choices=("sports","trading"))
    p.add_argument("--tenfold-db",type=Path)
    p.add_argument("--offline-proof-json",type=Path)
    args=p.parse_args(argv)
    try:
        states=observed_tenfold_states(args.tenfold_db) if args.tenfold_db else None
        proof={}
        if args.offline_proof_json:
            f=args.offline_proof_json
            if not f.is_file() or f.stat().st_size>50_000:
                raise ValueError("invalid local proof file")
            proof=json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(proof,dict):
                raise ValueError("proof requires a JSON mapping")
        out=five_gate_report(states,domain=Domain(args.domain),offline_proofs=proof)
        print(json.dumps(out,sort_keys=True,indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as e:
        print(json.dumps({"status":"EVIDENCE_UNAVAILABLE","reason":type(e).__name__,
                          "real_money_permitted":False}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
