"""Wolf-Coin application-state store: account/session/finance lifecycle.

SQLite transactions provide idempotent requests and durable recovery.
Website interaction and financial execution belong to the native Wolf Browser
host and its reconciled platform receipts, not a global paper/research mode.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from wolf_core.contracts import ContractError, Domain, utc_now
from .context_router import route_context
from .contracts import (
    BRIDGE_SCHEMA, MONEY_KEYS, NONNEGATIVE_KEYS, SESSION_STATES, SOURCES,
    TRANSACTION_KINDS, TRANSACTION_STATES, amount, check_no_secrets,
    currency, digest, ident, obj, parse_request, response, time,
)

SCHEMA_VERSION = 2
FRESH_SECONDS = 300
def session_tag(ref: str) -> str:
    """Derive internal identity from a nonsecret browser-local session label."""
    return sha256(("wolf-app-session-tag-v1|"+ident(ref,"session reference")).encode()).hexdigest()


READ_OPS = frozenset({
    "accounts.list", "account.read", "financial.overview",
    "activity.list", "decisions.list", "bridge.capabilities",
    "sync.plan", "sync.inbox", "financial.history", "context.route",
})
MUTATIONS = frozenset({
    "account.register", "account.remove", "session.record",
    "observation.ingest", "decision.propose", "decision.receipt",
    "sync.enqueue", "sync.claim", "sync.receipt",
    "sync.reconcile", "sync.cancel", "host.startup",
})
ALL_OPERATIONS = READ_OPS | MUTATIONS


class AppConflict(ContractError):
    """Stale, ambiguous, cross-session, or mismatched source input."""


class ApplicationStore:
    def __init__(self, database: str | Path):
        self.path = Path(database)
        if str(database) == ":memory:" or self.path.is_symlink():
            raise AppConflict("durable nonsymlink SQLite file required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not self.path.is_file():
            raise AppConflict("database is not a regular file")
        with closing(self._db()) as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS app_meta(
                  key TEXT PRIMARY KEY, value TEXT NOT NULL);
              INSERT OR IGNORE INTO app_meta VALUES ('schema','2');

              CREATE TABLE IF NOT EXISTS app_accounts(
                  domain TEXT NOT NULL, account_id TEXT NOT NULL,
                  platform_id TEXT NOT NULL, currency TEXT NOT NULL,
                  display_name TEXT NOT NULL, registered_at TEXT NOT NULL,
                  PRIMARY KEY(domain,account_id));

              CREATE TABLE IF NOT EXISTS app_sessions(
                  domain TEXT NOT NULL, account_id TEXT NOT NULL,
                  state TEXT NOT NULL, session_ref TEXT,
                  changed_at TEXT NOT NULL, device_id TEXT,
                  PRIMARY KEY(domain,account_id),
                  FOREIGN KEY(domain,account_id) REFERENCES app_accounts(domain,account_id)
                     ON DELETE CASCADE);

              CREATE TABLE IF NOT EXISTS app_observations(
                  domain TEXT NOT NULL, account_id TEXT NOT NULL,
                  observation_id TEXT NOT NULL, session_ref TEXT NOT NULL,
                  observed_at TEXT NOT NULL, source TEXT NOT NULL,
                  origin TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
                  fields_json TEXT NOT NULL, payload_digest TEXT NOT NULL,
                  PRIMARY KEY(domain,account_id,observation_id),
                  FOREIGN KEY(domain,account_id) REFERENCES app_accounts(domain,account_id)
                    ON DELETE CASCADE);

              CREATE TABLE IF NOT EXISTS app_transactions(
                  domain TEXT NOT NULL, account_id TEXT NOT NULL,
                  transaction_id TEXT NOT NULL, kind TEXT NOT NULL,
                  amount TEXT NOT NULL, status TEXT NOT NULL,
                  occurred_at TEXT NOT NULL, source_observation_id TEXT NOT NULL,
                  PRIMARY KEY(domain,account_id,transaction_id),
                  FOREIGN KEY(domain,account_id) REFERENCES app_accounts(domain,account_id)
                    ON DELETE CASCADE);

              CREATE TABLE IF NOT EXISTS app_decisions(
                  domain TEXT NOT NULL, account_id TEXT NOT NULL,
                  decision_id TEXT NOT NULL, observation_id TEXT NOT NULL,
                  instrument TEXT NOT NULL, action_kind TEXT NOT NULL,
                  proposed_amount TEXT NOT NULL, status TEXT NOT NULL,
                  result_ref TEXT, recorded_at TEXT NOT NULL,
                  PRIMARY KEY(domain,account_id,decision_id),
                  FOREIGN KEY(domain,account_id) REFERENCES app_accounts(domain,account_id)
                    ON DELETE CASCADE);

              CREATE TABLE IF NOT EXISTS app_sync_jobs(
                  domain TEXT NOT NULL, account_id TEXT NOT NULL,
                  job_id TEXT NOT NULL, reason TEXT NOT NULL,
                  status TEXT NOT NULL, created_at TEXT NOT NULL,
                  claimed_session_tag TEXT, result_observation_id TEXT,
                  claimed_at TEXT,
                  PRIMARY KEY(domain,account_id,job_id),
                  FOREIGN KEY(domain,account_id) REFERENCES app_accounts(domain,account_id)
                      ON DELETE CASCADE);

              CREATE TABLE IF NOT EXISTS app_audit(
                  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
                  event_kind TEXT NOT NULL, event_json TEXT NOT NULL,
                  previous_sha256 TEXT NOT NULL, record_sha256 TEXT NOT NULL,
                  happened_at TEXT NOT NULL);

              CREATE TABLE IF NOT EXISTS app_requests(
                  request_id TEXT PRIMARY KEY, input_sha256 TEXT NOT NULL,
                  response_json TEXT NOT NULL);
            """)
            v=db.execute("SELECT value FROM app_meta WHERE key='schema'").fetchone()
            if v is None:
                raise AppConflict("missing application-store schema")
            if v[0]=="1":
                # Preserve the historical event chain while removing legacy
                # research-only decision states from the application.
                self.verify_audit()
                db.execute("BEGIN IMMEDIATE")
                try:
                    old_count=db.execute("""SELECT COUNT(*) FROM app_decisions
                        WHERE status='RESEARCH_ONLY'""").fetchone()[0]
                    db.execute("""UPDATE app_decisions SET status='ANALYSIS_ARCHIVED'
                        WHERE status='RESEARCH_ONLY'""")
                    cached_count=0
                    for old_id,response_json in db.execute(
                            "SELECT request_id,response_json FROM app_requests").fetchall():
                        cached=json.loads(response_json)
                        if cached.get("status")=="RESEARCH_ONLY":
                            cached["status"]="ANALYSIS_ARCHIVED"
                            for obsolete in ("browser_action_authorized",
                                             "live_execution_authorized",
                                             "may_submit_order"):
                                cached.pop(obsolete,None)
                            cached["historical_analysis_record"]=True
                            db.execute("""UPDATE app_requests SET response_json=?
                                WHERE request_id=?""",(json.dumps(cached,sort_keys=True),old_id))
                            cached_count+=1
                    db.execute("UPDATE app_meta SET value='2' WHERE key='schema'")
                    self._audit(db,"app-schema-v1-to-v2","schema.migrate",{
                        "from":1,"to":2,"archived_legacy_analysis":old_count,
                        "archived_cached_responses":cached_count,
                        "execution_status":"NO_PLATFORM_EFFECT_FROM_MIGRATION"})
                    db.execute("COMMIT")
                except BaseException:
                    db.execute("ROLLBACK")
                    raise
                v=("2",)
            if v[0]!=str(SCHEMA_VERSION):
                raise AppConflict("unsupported application-store schema")
        if os.name == "posix":
            os.chmod(self.path, 0o600)

    def _db(self):
        db=sqlite3.connect(str(self.path),timeout=10,isolation_level=None)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _scope(payload: dict) -> tuple[str,str]:
        domain=payload.get("domain")
        if domain not in ("sports","trading") or type(domain) is not str:
            raise ContractError("invalid account domain")
        return domain, ident(payload.get("account_id"),"account ID")

    @staticmethod
    def _require_account(db, scope: tuple[str,str]) -> tuple:
        row=db.execute("""SELECT platform_id,currency,display_name,registered_at
                       FROM app_accounts WHERE domain=? AND account_id=?""",scope).fetchone()
        if row is None:
            raise AppConflict("account not registered")
        return row

    @staticmethod
    def _session(db,scope:tuple[str,str])->tuple:
        row=db.execute("""SELECT state,session_ref,changed_at FROM app_sessions
                          WHERE domain=? AND account_id=?""",scope).fetchone()
        if row is None:
            raise AppConflict("session state missing")
        return row

    @staticmethod
    def _audit(db,event_id:str,kind:str,data:dict)->None:
        previous=db.execute("SELECT record_sha256 FROM app_audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous_hash=previous[0] if previous else "0"*64
        occurred=utc_now()
        content=json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        record_hash=sha256(json.dumps(
            {"event_id":event_id,"kind":kind,"data":data,"previous":previous_hash,"occurred_at":occurred},
            sort_keys=True,separators=(",",":"),ensure_ascii=False
        ).encode()).hexdigest()
        db.execute("""INSERT INTO app_audit
            (event_id,event_kind,event_json,previous_sha256,record_sha256,happened_at)
            VALUES (?,?,?,?,?,?)""",(event_id,kind,content,previous_hash,record_hash,occurred))

    def verify_audit(self) -> int:
        with closing(self._db()) as db:
            return self.verify_audit_connection(db)

    @staticmethod
    def verify_audit_connection(db) -> int:
        """Check an existing DB connection without initiating a schema migration."""
        rows=db.execute("""SELECT seq,event_id,event_kind,event_json,previous_sha256,
                 record_sha256,happened_at FROM app_audit ORDER BY seq""").fetchall()
        previous="0"*64
        for position,(seq,event_id,kind,payload,prev,recorded,when) in enumerate(rows,1):
            if seq!=position or prev!=previous:
                raise AppConflict("app audit chain broken")
            obj_data=json.loads(payload)
            expected=sha256(json.dumps(
                {"event_id":event_id,"kind":kind,"data":obj_data,"previous":prev,"occurred_at":when},
                sort_keys=True,separators=(",",":"),ensure_ascii=False
            ).encode()).hexdigest()
            if recorded!=expected or json.dumps(obj_data,sort_keys=True,separators=(",",":"),ensure_ascii=False)!=payload:
                raise AppConflict("app audit record mismatch")
            previous=recorded
        return len(rows)

    def handle(self, value:dict) -> dict:
        request_id,operation,payload=parse_request(value)
        if operation not in ALL_OPERATIONS:
            raise ContractError("unknown bridge operation")
        if operation=="bridge.capabilities":
            return response(request_id,"OK",{
                "operations":sorted(ALL_OPERATIONS),
                "supports":["windows-python","linux-python","android-host-port-required"],
                "browser_adapter_connected":False,
                "network_listener":False,
                "credential_storage":False,
                "all_observations_external_unverified":True,
                "financial_intent_kinds":[
                    "PLACE_BET","CANCEL_BET","PLACE_TRADE","CLOSE_POSITION"],
                "financial_workflow":"CONTEXTUAL_NATIVE_BROWSER_HANDOFF",
                "native_host_adapter":"REQUIRES_APPLICATION_BINDING",
                "transport_authentication":"NATIVE_HOST_REQUIRED",
            })
        if operation in READ_OPS:
            return response(request_id,"OK",self._read(operation,payload))
        payload_hash=digest(value)
        with closing(self._db()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing=db.execute("""SELECT input_sha256,response_json FROM app_requests
                                      WHERE request_id=?""",(request_id,)).fetchone()
                if existing:
                    if existing[0]!=payload_hash:
                        raise AppConflict("request ID reused for different command")
                    output=json.loads(existing[1])
                else:
                    output=self._mutate(db,request_id,operation,payload)
                    db.execute("INSERT INTO app_requests VALUES (?,?,?)",
                               (request_id,payload_hash,json.dumps(output,sort_keys=True)))
                db.execute("COMMIT")
                return response(request_id,"OK",output)
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def _mutate(self,db,request_id:str,operation:str,payload:dict)->dict:
        check_no_secrets(payload)
        if operation=="host.startup":
            obj(payload,{"host_instance_id"})
            ident(payload["host_instance_id"],"native host instance")
            active=db.execute("SELECT COUNT(*) FROM app_sessions WHERE state='ACTIVE'").fetchone()[0]
            claimed=db.execute("""SELECT COUNT(*) FROM app_sync_jobs
                  WHERE status='CLAIMED'""").fetchone()[0]
            now=utc_now()
            # A restored browser must independently revalidate auth; a valid
            # persisted account is not a live authenticated session.
            db.execute("""UPDATE app_sessions SET state='PAUSED',
                 changed_at=? WHERE state='ACTIVE'""",(now,))
            db.execute("""UPDATE app_sync_jobs SET status='UNKNOWN'
                 WHERE status='CLAIMED'""")
            self._audit(db,request_id,"host.startup",{
                "host_instance_id":payload["host_instance_id"],
                "previous_active_sessions":active,"ambiguous_sync_claims":claimed})
            return {"accounts_preserved":True,
                    "sessions_requiring_revalidation":active,
                    "inflight_browser_tasks_marked_unknown":claimed,
                    "live_session_assumed":False,
                    "browser_reauthentication_or_restore_required":True}
        if operation=="account.register":
            obj(payload,{"domain","account_id","platform_id","currency","display_name"})
            scope=self._scope(payload)
            platform=ident(payload["platform_id"],"platform ID")
            code=currency(payload["currency"])
            name=payload["display_name"]
            if not isinstance(name,str) or not 1<=len(name)<=80 or any(ord(c)<32 for c in name):
                raise ContractError("invalid account display name")
            if db.execute("SELECT 1 FROM app_accounts WHERE domain=? AND account_id=?",scope).fetchone():
                raise AppConflict("account already registered; explicit account removal required")
            when=utc_now()
            db.execute("INSERT INTO app_accounts VALUES (?,?,?,?,?,?)",
                       (*scope,platform,code,name,when))
            db.execute("INSERT INTO app_sessions VALUES (?,?,?,?,?,?)",
                       (*scope,"LOGGED_OUT",None,when,None))
            self._audit(db,request_id,operation,{"domain":scope[0],"account_id":scope[1]})
            return {"account_id":scope[1],"domain":scope[0],
                    "registration":"PERSISTENT","session_state":"LOGGED_OUT",
                    "credential_storage":False}
        if operation=="account.remove":
            obj(payload,{"domain","account_id"})
            scope=self._scope(payload)
            self._require_account(db,scope)
            db.execute("DELETE FROM app_accounts WHERE domain=? AND account_id=?",scope)
            self._audit(db,request_id,operation,{"domain":scope[0],"account_id":scope[1],
                "associated_session_and_financial_records_deleted":True})
            return {"registration":"REMOVED","associated_state_erased":True,
                    "browser_credential_cleanup":"FRONTEND_HOST_REQUIRED"}
        if operation=="session.record":
            obj(payload,{"domain","account_id","state","observed_at"},
                {"session_ref","device_id"})
            scope=self._scope(payload)
            self._require_account(db,scope)
            state=payload["state"]
            if state not in SESSION_STATES:
                raise ContractError("invalid session state")
            seen=time(payload["observed_at"])
            prev_state,previous_ref,changed=self._session(db,scope)
            if seen < changed:
                raise AppConflict("stale session event rejected")
            if state=="ACTIVE":
                ref=session_tag(payload.get("session_ref"))
            else:
                ref=previous_ref if state=="OFFLINE" or state=="PAUSED" else None
            device=(ident(payload["device_id"],"device ID")
                    if "device_id" in payload else None)
            db.execute("""UPDATE app_sessions SET state=?,session_ref=?,
                changed_at=?,device_id=COALESCE(?,device_id)
                WHERE domain=? AND account_id=?""",
                       (state,ref,seen,device,*scope))
            self._audit(db,request_id,operation,{"domain":scope[0],"account_id":scope[1],
                       "state":state,"observed_at":seen})
            return {"session_state":state,"registered":True,
                    "credentials_preserved_in_browser_only":True}
        if operation=="observation.ingest":
            return self._ingest(db,request_id,payload)
        if operation=="decision.propose":
            return self._propose(db,request_id,payload)
        if operation=="decision.receipt":
            return self._receipt(db,request_id,payload)
        if operation=="sync.enqueue":
            return self._sync_enqueue(db,request_id,payload)
        if operation=="sync.claim":
            return self._sync_claim(db,request_id,payload)
        if operation=="sync.receipt":
            return self._sync_receipt(db,request_id,payload)
        if operation=="sync.reconcile":
            return self._sync_reconcile(db,request_id,payload)
        if operation=="sync.cancel":
            return self._sync_cancel(db,request_id,payload)
        raise ContractError("unknown mutation")

    def _ingest(self,db,request_id,payload):
        obj(payload,{"domain","account_id","observation_id","session_ref",
                     "observed_at","source","origin","evidence_sha256","fields"},
            {"transactions"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        session_state,session_ref,_=self._session(db,scope)
        if session_state!="ACTIVE" or session_ref!=session_tag(payload["session_ref"]):
            raise AppConflict("not an active matching browser session")
        obs_id=ident(payload["observation_id"],"observation ID")
        observed=time(payload["observed_at"])
        if payload["source"] not in SOURCES:
            raise ContractError("unsupported browser evidence source")
        origin=payload["origin"]
        if (not isinstance(origin,str) or len(origin)>253 or
            not all(c.isalnum() or c in ".-" for c in origin) or
            origin.startswith(".") or "/" in origin or ":" in origin):
            raise ContractError("browser origin must be hostname only")
        proof=payload["evidence_sha256"]
        if not isinstance(proof,str) or not re_hex(proof):
            raise ContractError("evidence SHA-256 required")
        raw_fields=payload["fields"]
        if not isinstance(raw_fields,dict) or not raw_fields or set(raw_fields)-MONEY_KEYS:
            raise ContractError("financial fields out of contract")
        fields={key:amount(v,nonnegative=(key in NONNEGATIVE_KEYS))
                for key,v in raw_fields.items()}
        tx_list=payload.get("transactions",[])
        if not isinstance(tx_list,list) or len(tx_list)>100:
            raise ContractError("invalid observation transaction batch")
        tuples=[]
        seen_ids=set()
        for tx in tx_list:
            obj(tx,{"transaction_id","kind","amount","status","occurred_at"})
            name=ident(tx["transaction_id"],"transaction ID")
            if name in seen_ids:
                raise AppConflict("duplicate transaction in observation")
            seen_ids.add(name)
            kind=tx["kind"]
            status=tx["status"]
            if kind not in TRANSACTION_KINDS or status not in TRANSACTION_STATES:
                raise ContractError("invalid transaction kind/status")
            cost=amount(tx["amount"],nonnegative=True)
            happened=time(tx["occurred_at"])
            if happened>observed:
                raise AppConflict("transaction cannot occur after observation capture")
            tuples.append((name,kind,cost,status,happened))
        canonical_payload=digest(payload)
        found=db.execute("""SELECT payload_digest FROM app_observations WHERE
                      domain=? AND account_id=? AND observation_id=?""",(*scope,obs_id)).fetchone()
        if found:
            if found[0]!=canonical_payload:
                raise AppConflict("observation ID reused with changed financial evidence")
            return {"observation_id":obs_id,"idempotent":True,"verification":"UNVERIFIED"}
        current=db.execute("""SELECT observed_at FROM app_observations
                      WHERE domain=? AND account_id=? ORDER BY observed_at DESC LIMIT 1""",scope).fetchone()
        # Store raw chronological history for audit, but never let an older
        # observation become the effective latest account snapshot.
        older=bool(current and observed < current[0])
        db.execute("""INSERT INTO app_observations VALUES (?,?,?,?,?,?,?,?,?,?)""",
                   (*scope,obs_id,session_ref,observed,payload["source"],origin,proof,
                    json.dumps(fields,sort_keys=True),canonical_payload))
        new_transactions=0
        for name,kind,cost,status,happened in tuples:
            old=db.execute("""SELECT kind,amount,status,occurred_at FROM app_transactions
                    WHERE domain=? AND account_id=? AND transaction_id=?""",(*scope,name)).fetchone()
            if old is None:
                db.execute("""INSERT INTO app_transactions VALUES (?,?,?,?,?,?,?,?)""",
                           (*scope,name,kind,cost,status,happened,obs_id))
                new_transactions+=1
            else:
                old_kind,old_amount,old_status,old_when=old
                if (old_kind,old_amount,old_when)!=(kind,cost,happened):
                    raise AppConflict("transaction identity reused for different money/identity")
                if old_status!=status:
                    if old_status!="PENDING" or status not in ("SETTLED","CANCELLED"):
                        raise AppConflict("invalid transaction settlement transition")
                    db.execute("""UPDATE app_transactions SET status=?,source_observation_id=?
                        WHERE domain=? AND account_id=? AND transaction_id=?""",
                        (status,obs_id,*scope,name))
        self._audit(db,request_id,"observation.ingest",{"domain":scope[0],"account_id":scope[1],
                    "observation_id":obs_id,"source":payload["source"],
                    "older_than_previous":older,"transactions_added":new_transactions})
        return {"observation_id":obs_id,"idempotent":False,"stored":True,
                "older_than_previous":older,"transactions_added":new_transactions,
                "verification":"UNVERIFIED","requires_platform_readback":True}

    def _propose(self,db,request_id,payload):
        obj(payload,{"domain","account_id","decision_id","observation_id",
                     "instrument","action_kind","proposed_amount"},
            {"browser_capabilities","platform_permissions","money_budget","target_id"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        session=self._session(db,scope)
        decision_id=ident(payload["decision_id"],"decision ID")
        observation_id=ident(payload["observation_id"],"observation ID")
        instrument=ident(payload["instrument"],"instrument")
        kind=payload["action_kind"]
        size=amount(payload["proposed_amount"],nonnegative=True)
        if Decimal(size)<=0 and kind not in ("CANCEL_BET","CLOSE_POSITION"):
            raise ContractError("positive proposed amount required for placements")
        detail=self._account_detail(scope)
        transaction_goals=("PLACE_BET","CANCEL_BET","PLACE_TRADE","CLOSE_POSITION")
        financial=kind in transaction_goals
        if financial:
            selected=route_context(
                goal=kind,account=detail,
                capabilities=payload.get("browser_capabilities",[]),
                permissions=payload.get("platform_permissions",[]),
                target=payload.get("target_id"),
                requested_amount=size,money_budget=payload.get("money_budget"))
            if selected["state"]!="READY":
                # Not a feature lock: select the next useful step, without
                # asserting a money effect or silently changing its budget.
                return {"decision_id":decision_id,"status":"CONTEXT_STEP_REQUIRED",
                        "selected_next_step":selected["next_step"],
                        "reason":selected["context_reasons"],
                        "capability_available_for_future_context":True}
        else:
            raise ContractError(
                "decision.propose expects a financial action; use context.route "
                "for LEARN, RESEARCH or ANALYZE")
        if session[0]!="ACTIVE":
            raise AppConflict("no active session for proposal")
        if (detail["freshness"]!="CURRENT_UNVERIFIED" or
            detail["reconciliation"]["status"]=="CONFLICT"):
            raise AppConflict("financial evidence is stale or conflicting")
        obs=db.execute("""SELECT observed_at,session_ref FROM app_observations
               WHERE domain=? AND account_id=? AND observation_id=?""",(*scope,observation_id)).fetchone()
        if obs is None or obs[1]!=session[1]:
            raise AppConflict("proposal lacks current-session observation evidence")
        latest=db.execute("""SELECT observation_id FROM app_observations
            WHERE domain=? AND account_id=? ORDER BY observed_at DESC,observation_id DESC LIMIT 1""",
            scope).fetchone()
        if latest is None or latest[0]!=observation_id:
            raise AppConflict("proposal references stale evidence")
        if datetime.now(timezone.utc)-datetime.fromisoformat(obs[0])>timedelta(seconds=FRESH_SECONDS):
            raise AppConflict("proposal evidence no longer fresh")
        if db.execute("""SELECT 1 FROM app_decisions WHERE domain=? AND account_id=? AND decision_id=?""",
                      (*scope,decision_id)).fetchone():
            raise AppConflict("decision identity already used")
        next_status="BROWSER_HANDOFF_READY"
        db.execute("INSERT INTO app_decisions VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (*scope,decision_id,observation_id,instrument,kind,size,
                    next_status,None,utc_now()))
        self._audit(db,request_id,"decision.propose",{"domain":scope[0],"account_id":scope[1],
                    "decision_id":decision_id,"status":next_status,
                    "observation_id":observation_id,"action_kind":kind})
        return {"decision_id":decision_id,"status":next_status,
                "context_selection":selected,
                "native_workflow_ready":True,
                "browser_action_executed":False,
                "requires_platform_result_and_reconciliation":True}
    def _receipt(self,db,request_id,payload):
        obj(payload,{"domain","account_id","decision_id","outcome","result_ref"},
            {"receipt_evidence_sha256"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        decision=ident(payload["decision_id"],"decision ID")
        result_ref=ident(payload["result_ref"],"receipt reference")
        prev=db.execute("""SELECT status,result_ref FROM app_decisions
                  WHERE domain=? AND account_id=? AND decision_id=?""",(*scope,decision)).fetchone()
        if prev is None or prev[0]!="BROWSER_HANDOFF_READY":
            raise AppConflict("financial decision not awaiting a native browser receipt")
        outcome=payload["outcome"]
        if outcome not in ("NOT_EXECUTED","CANCELLED","UNKNOWN",
                           "NATIVE_REPORTED_SUBMITTED","NATIVE_REPORTED_REJECTED"):
            raise ContractError("unsupported native browser result")
        if outcome=="NATIVE_REPORTED_SUBMITTED":
            if not re_hex(payload.get("receipt_evidence_sha256")):
                raise ContractError("native submission requires bound receipt evidence")
            terminal="AWAITING_PLATFORM_RECONCILIATION"
        else:
            if "receipt_evidence_sha256" in payload:
                raise ContractError("no submission evidence for this outcome")
            terminal=outcome
        db.execute("""UPDATE app_decisions SET status=?,result_ref=?
               WHERE domain=? AND account_id=? AND decision_id=?""",
               (terminal,result_ref,*scope,decision))
        self._audit(db,request_id,"decision.receipt",{"domain":scope[0],"account_id":scope[1],
                    "decision_id":decision,"outcome":outcome,
                    "result_ref":result_ref,
                    "native_receipt_evidence_sha256":payload.get("receipt_evidence_sha256")})
        return {"status":terminal,
                "requires_authoritative_platform_readback":
                    terminal=="AWAITING_PLATFORM_RECONCILIATION",
                "browser_result_is_self_reported":True,
                "duplicate_dispatch_possible":False}

    def _sync_enqueue(self,db,request_id,payload):
        obj(payload,{"domain","account_id","job_id","reason"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        job=ident(payload["job_id"],"sync job identity")
        reason=payload["reason"]
        if reason not in ("ON_LOGIN","MANUAL","PERIODIC","RECONNECT","STARTUP"):
            raise ContractError("unknown sync reason")
        existing=db.execute("""SELECT 1 FROM app_sync_jobs WHERE
               domain=? AND account_id=? AND job_id=?""",(*scope,job)).fetchone()
        if existing:
            raise AppConflict("sync job ID already used")
        # A single in-flight job per account prevents stacking browser
        # work or duplicate requests during outages/restarts.
        busy=db.execute("""SELECT 1 FROM app_sync_jobs WHERE
            domain=? AND account_id=? AND status IN
             ('PENDING','WAITING_LOGIN','CLAIMED','UNKNOWN')
            LIMIT 1""",scope).fetchone()
        if busy:
            raise AppConflict("sync job pending or ambiguous; reconcile first")
        state=self._session(db,scope)[0]
        status="PENDING" if state=="ACTIVE" else "WAITING_LOGIN"
        db.execute("INSERT INTO app_sync_jobs VALUES (?,?,?,?,?,?,?,?,?)",
                   (*scope,job,reason,status,utc_now(),None,None,None))
        self._audit(db,request_id,"sync.enqueue",{
            "domain":scope[0],"account_id":scope[1],"job_id":job,"status":status})
        return {"job_id":job,"status":status,"browser_work_executed":False,
                "operation_requested":"OBSERVE_ACCOUNT","live_effect_authorized":False}

    def _sync_claim(self,db,request_id,payload):
        obj(payload,{"domain","account_id","job_id","session_ref"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        job=ident(payload["job_id"],"sync job identity")
        session=self._session(db,scope)
        tag=session_tag(payload["session_ref"])
        if session[0]!="ACTIVE" or session[1]!=tag:
            raise AppConflict("no active matching session for browser-work claim")
        row=db.execute("""SELECT status FROM app_sync_jobs WHERE
            domain=? AND account_id=? AND job_id=?""",(*scope,job)).fetchone()
        if row is None or row[0] not in ("PENDING","WAITING_LOGIN"):
            raise AppConflict("work previously claimed or not queued; no replay")
        db.execute("""UPDATE app_sync_jobs SET status='CLAIMED',
            claimed_session_tag=?, claimed_at=?
            WHERE domain=? AND account_id=? AND job_id=?""",
            (tag,utc_now(),*scope,job))
        self._audit(db,request_id,"sync.claim",{
            "domain":scope[0],"account_id":scope[1],"job_id":job})
        return {
            "job_id":job,"status":"CLAIMED",
            "browser_command":{"kind":"OBSERVE_ACCOUNT",
                "allowed_evidence_sources":sorted(SOURCES),
                "no_credentials_in_payload":True,
                "requires_native_host_session_authorization":True},
            "operation_class":"OBSERVATION",
        }

    def _sync_receipt(self,db,request_id,payload):
        obj(payload,{"domain","account_id","job_id","outcome"},
            {"observation_id"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        job=ident(payload["job_id"],"sync job identity")
        outcome=payload["outcome"]
        if outcome not in ("OBSERVED","FAILED","UNKNOWN"):
            raise ContractError("sync outcome must be observable or ambiguous")
        row=db.execute("""SELECT status,claimed_session_tag,claimed_at FROM app_sync_jobs
            WHERE domain=? AND account_id=? AND job_id=?""",(*scope,job)).fetchone()
        if row is None or row[0]!="CLAIMED":
            raise AppConflict("work not in claimed state; no automatic retry")
        if outcome=="OBSERVED":
            obs_id=ident(payload.get("observation_id"),"observation ID")
            observed=db.execute("""SELECT session_ref,observed_at FROM app_observations
                WHERE domain=? AND account_id=? AND observation_id=?""",
                (*scope,obs_id)).fetchone()
            if observed is None or observed[0]!=row[1] or observed[1]<row[2]:
                raise AppConflict("sync receipt requires newly captured same-session observation")
            status="DONE"
        else:
            if "observation_id" in payload:
                raise ContractError("failure/unknown receipt must not assert financial observation")
            obs_id=None
            status="UNKNOWN" if outcome=="UNKNOWN" else "FAILED"
        db.execute("""UPDATE app_sync_jobs SET status=?,result_observation_id=?
            WHERE domain=? AND account_id=? AND job_id=?""",
            (status,obs_id,*scope,job))
        self._audit(db,request_id,"sync.receipt",{
            "domain":scope[0],"account_id":scope[1],"job_id":job,
            "status":status,"observation_id":obs_id})
        return {"job_id":job,"status":status,
                "browser_effect_replay_allowed":False,
                "operation_class":"OBSERVATION"}

    def _sync_reconcile(self,db,request_id,payload):
        obj(payload,{"domain","account_id","job_id","observation_id","session_ref"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        job=ident(payload["job_id"],"sync job identity")
        obs_id=ident(payload["observation_id"],"observation ID")
        current=self._session(db,scope)
        tag=session_tag(payload["session_ref"])
        if current[0]!="ACTIVE" or current[1]!=tag:
            raise AppConflict("recovery needs current revalidated browser session")
        pending=db.execute("""SELECT status,claimed_at FROM app_sync_jobs
                WHERE domain=? AND account_id=? AND job_id=?""",(*scope,job)).fetchone()
        if pending is None or pending[0]!="UNKNOWN":
            raise AppConflict("no ambiguous work awaiting reconciliation")
        observed=db.execute("""SELECT observed_at,session_ref FROM app_observations
                WHERE domain=? AND account_id=? AND observation_id=?""",
                (*scope,obs_id)).fetchone()
        if (observed is None or observed[1]!=tag or
            observed[0]<current[2] or observed[0]<pending[1]):
            raise AppConflict("recovery requires fresh current-session observation readback")
        db.execute("""UPDATE app_sync_jobs SET status='DONE',
                      result_observation_id=?
                      WHERE domain=? AND account_id=? AND job_id=?""",
                      (obs_id,*scope,job))
        self._audit(db,request_id,"sync.reconcile",{
            "domain":scope[0],"account_id":scope[1],"job_id":job,
            "observation_id":obs_id,"review":"CURRENT_SESSION_OBSERVED"})
        return {"job_id":job,"status":"DONE",
                "recovered_from_unknown":True,
                "automatic_replay_performed":False,
                "operation_class":"OBSERVATION"}

    def _sync_cancel(self,db,request_id,payload):
        obj(payload,{"domain","account_id","job_id","reason"})
        scope=self._scope(payload)
        self._require_account(db,scope)
        job=ident(payload["job_id"],"sync job identity")
        if payload["reason"] not in ("USER_REQUESTED","NATIVE_HOST_RECOVERY"):
            raise ContractError("explicit cancellation reason required")
        row=db.execute("""SELECT status FROM app_sync_jobs
                WHERE domain=? AND account_id=? AND job_id=?""",(*scope,job)).fetchone()
        if row is None or row[0] not in ("UNKNOWN","PENDING","WAITING_LOGIN"):
            raise AppConflict("only unknown/queued nonfinancial work may be cancelled")
        db.execute("""UPDATE app_sync_jobs SET status='CANCELLED' WHERE
                  domain=? AND account_id=? AND job_id=?""",(*scope,job))
        self._audit(db,request_id,"sync.cancel",{
            "domain":scope[0],"account_id":scope[1],"job_id":job,
            "reason":payload["reason"]})
        return {"job_id":job,"status":"CANCELLED","was_not_automatically_retried":True,
                "last_known_financial_data_may_remain_stale":True,
                "operation_class":"OBSERVATION"}

    def _read(self,operation,payload):
        if operation=="context.route":
            obj(payload,{"goal","capabilities","permissions"},
                {"domain","account_id","target_id","requested_amount","money_budget"})
            if ("domain" in payload)!=( "account_id" in payload):
                raise ContractError("account domain and ID must be supplied together")
            context=(self._account_detail(self._scope(payload))
                     if "domain" in payload else None)
            return route_context(
                goal=payload["goal"], account=context,
                capabilities=payload["capabilities"],permissions=payload["permissions"],
                target=payload.get("target_id"),
                requested_amount=payload.get("requested_amount"),
                money_budget=payload.get("money_budget"),
            )
        if operation=="accounts.list":
            obj(payload,set())
            with closing(self._db()) as db:
                rows=db.execute("""SELECT a.domain,a.account_id FROM app_accounts a
                                  ORDER BY a.domain,a.account_id""").fetchall()
            return {"accounts":[self._account_detail((domain,account_id)) for domain,account_id in rows]}
        if operation=="account.read":
            obj(payload,{"domain","account_id"})
            return self._account_detail(self._scope(payload))
        if operation=="financial.overview":
            obj(payload,set())
            all_accounts=self._read("accounts.list",{})["accounts"]
            totals:dict[str,dict[str,Decimal]]={}
            for entry in all_accounts:
                if entry["freshness"]!="CURRENT_UNVERIFIED" or not entry["latest_financial"]:
                    continue
                bucket=totals.setdefault(entry["currency"],{})
                for key,value in entry["latest_financial"]["fields"].items():
                    bucket[key]=bucket.get(key,Decimal(0))+Decimal(value)
            return {"accounts":all_accounts,
                    "currency_totals":{code:{k:str(v) for k,v in values.items()}
                                       for code,values in totals.items()},
                    "totals_scope":"PER_CURRENCY_CURRENT_UNVERIFIED_ONLY",
                    "cross_currency_conversion":False,
                    "settled_funds_verified":False}
        if operation=="sync.plan":
            obj(payload,set(),{"minimum_interval_seconds"})
            seconds=payload.get("minimum_interval_seconds",60)
            if type(seconds) is not int or not 30<=seconds<=86400:
                raise ContractError("invalid sync cadence")
            accounts=self._read("accounts.list",{})["accounts"]
            commands=[]
            with closing(self._db()) as db:
                for item in accounts:
                    scope=(item["domain"],item["account_id"])
                    pending=db.execute("""SELECT job_id,status FROM app_sync_jobs WHERE
                        domain=? AND account_id=? AND status IN
                        ('PENDING','WAITING_LOGIN','CLAIMED','UNKNOWN')
                        ORDER BY created_at DESC LIMIT 1""",scope).fetchone()
                    if pending:
                        status="WAITING_FOR_READBACK" if pending[1] in ("CLAIMED","UNKNOWN") else "ALREADY_QUEUED"
                    elif item["session_state"]!="ACTIVE":
                        status="WAITING_FOR_LOGIN"
                    else:
                        previous=item["latest_financial"]
                        due=(item["freshness"]!="CURRENT_UNVERIFIED" or
                             previous is None or
                             datetime.now(timezone.utc)-datetime.fromisoformat(
                                 previous["observed_at"]) >= timedelta(seconds=seconds))
                        status="ENQUEUE_OBSERVE_ACCOUNT" if due else "UP_TO_DATE_UNVERIFIED"
                    commands.append({"domain":scope[0],"account_id":scope[1],
                        "recommendation":status,"browser_operation":"OBSERVE_ACCOUNT",
                        "backend_submitted":False})
            return {"accounts":commands,"cadence_suggestion_seconds":seconds,
                    "planner_read_only":True,"actual_scheduler":"NATIVE_HOST_REQUIRED",
                    "live_execution_available":False}
        if operation=="sync.inbox":
            obj(payload,{"domain","account_id"})
            scope=self._scope(payload)
            with closing(self._db()) as db:
                self._require_account(db,scope)
                rows=db.execute("""SELECT job_id,reason,status,created_at,
                  result_observation_id FROM app_sync_jobs
                  WHERE domain=? AND account_id=? ORDER BY created_at,job_id""",
                  scope).fetchall()
            return {"jobs":[dict(zip(("job_id","reason","status",
                "created_at","result_observation_id"),x)) for x in rows],
                "automatic_ambiguous_replay":False}
        if operation=="financial.history":
            obj(payload,{"domain","account_id","kind"},
                {"limit","offset","since","until"})
            scope=self._scope(payload)
            kind=payload["kind"]
            if kind not in ("TRANSACTIONS","OBSERVATIONS"):
                raise ContractError("unsupported history kind")
            limit=payload.get("limit",100)
            offset=payload.get("offset",0)
            if type(limit) is not int or not 1<=limit<=500:
                raise ContractError("history limit out of range")
            if type(offset) is not int or not 0<=offset<=10000:
                raise ContractError("history offset out of range")
            since=time(payload["since"]) if "since" in payload else None
            until=time(payload["until"]) if "until" in payload else None
            if since and until and since>until:
                raise ContractError("invalid history time window")
            with closing(self._db()) as db:
                self._require_account(db,scope)
                constraints=["domain=?","account_id=?"]
                args=[*scope]
                stamp="occurred_at" if kind=="TRANSACTIONS" else "observed_at"
                if since:
                    constraints.append(stamp+">=?")
                    args.append(since)
                if until:
                    constraints.append(stamp+"<=?")
                    args.append(until)
                where=" AND ".join(constraints)
                if kind=="TRANSACTIONS":
                    sql=(f"""SELECT transaction_id,kind,amount,status,occurred_at,
                             source_observation_id FROM app_transactions WHERE {where}
                             ORDER BY occurred_at DESC, transaction_id DESC LIMIT ? OFFSET ?""")
                    labels=("transaction_id","kind","amount","status","occurred_at",
                            "source_observation_id")
                else:
                    sql=(f"""SELECT observation_id,session_ref,observed_at,source,
                             origin,evidence_sha256,fields_json FROM app_observations WHERE {where}
                             ORDER BY observed_at DESC, observation_id DESC LIMIT ? OFFSET ?""")
                    labels=("observation_id","session_tag","observed_at","source",
                            "origin","evidence_sha256","fields")
                rows=db.execute(sql,(*args,limit,offset)).fetchall()
            entries=[]
            for raw in rows:
                entry=dict(zip(labels,raw))
                if kind=="OBSERVATIONS":
                    entry["fields"]=json.loads(entry["fields"])
                    entry.pop("session_tag",None)
                entry["verification"]="UNVERIFIED_PLATFORM_REPORTED"
                entries.append(entry)
            return {"kind":kind,"domain":scope[0],"account_id":scope[1],
                    "entries":entries,"limit":limit,"offset":offset,
                    "next_offset":offset+len(entries) if len(entries)==limit else None,
                    "platform_settlement_credibility":"NOT_EXTERNALLY_VERIFIED",
                    "sensitive_session_values_excluded":True}
        if operation=="activity.list":
            obj(payload,set(),{"limit"})
            limit=payload.get("limit",50)
            if type(limit) is not int or not 1<=limit<=200:
                raise ContractError("activity limit out of range")
            self.verify_audit()
            with closing(self._db()) as db:
                rows=db.execute("""SELECT seq,event_kind,event_json,happened_at FROM app_audit
                         ORDER BY seq DESC LIMIT ?""",(limit,)).fetchall()
            return {"events":[{"seq":seq,"kind":kind,"detail":json.loads(detail),
                               "occurred_at":occurred} for seq,kind,detail,occurred in rows],
                    "hash_chain_checked":True,"external_anchor":False}
        if operation=="decisions.list":
            obj(payload,{"domain","account_id"})
            scope=self._scope(payload)
            with closing(self._db()) as db:
                self._require_account(db,scope)
                rows=db.execute("""SELECT decision_id,observation_id,instrument,
                         action_kind,proposed_amount,status,result_ref,recorded_at
                         FROM app_decisions WHERE domain=? AND account_id=?
                         ORDER BY recorded_at,decision_id""",scope).fetchall()
            return {"decisions":[dict(zip(("decision_id","observation_id","instrument",
                "action_kind","proposed_amount","status","result_ref","recorded_at"),row)) for row in rows],
                "execution_handoff":"NATIVE_BROWSER",
                "requires_platform_readback":True}
        raise ContractError("unsupported read")

    def _account_detail(self,scope):
        with closing(self._db()) as db:
            row=self._require_account(db,scope)
            state,session_ref,session_when=self._session(db,scope)
            device_row=db.execute("""SELECT device_id FROM app_sessions
                 WHERE domain=? AND account_id=?""",scope).fetchone()
            device_id=device_row[0] if device_row else None
            latest=db.execute("""SELECT observation_id,observed_at,source,
                    origin,evidence_sha256,fields_json,session_ref FROM app_observations
                    WHERE domain=? AND account_id=?
                    ORDER BY observed_at DESC,observation_id DESC LIMIT 1""",scope).fetchone()
            transactions=db.execute("""SELECT transaction_id,kind,amount,status,occurred_at
                  FROM app_transactions WHERE domain=? AND account_id=?
                  ORDER BY occurred_at DESC,transaction_id DESC LIMIT 150""",scope).fetchall()
            count=db.execute("""SELECT COUNT(*) FROM app_observations
                  WHERE domain=? AND account_id=?""",scope).fetchone()[0]
            # Corroboration is between distinct observation channels; even
            # corroborated browser values are NOT authoritative platform truth.
            neighboring=db.execute("""SELECT observation_id,observed_at,source,
                     fields_json,session_ref FROM app_observations
                     WHERE domain=? AND account_id=?
                     ORDER BY observed_at DESC,observation_id DESC LIMIT 30""",scope).fetchall()
        freshness="NO_OBSERVATION"
        reconciliation={"status":"NO_OBSERVATION","conflicting_fields":[],
                        "independently_platform_verified":False}
        snapshot=None
        if latest:
            obs_id,when,source,origin,proof,values,observation_session=latest
            snapshot={"observation_id":obs_id,"observed_at":when,"source":source,
                      "origin":origin,"evidence_sha256":proof,
                      "fields":json.loads(values),"verification":"UNVERIFIED"}
            age=datetime.now(timezone.utc)-datetime.fromisoformat(when)
            freshness=("CURRENT_UNVERIFIED" if state=="ACTIVE" and
                        observation_session==session_ref and
                        when>=session_when and
                        age<=timedelta(seconds=FRESH_SECONDS) and age>=timedelta(seconds=-300)
                       else "STALE_LAST_KNOWN")
            corroborating=[]
            latest_dt=datetime.fromisoformat(when)
            for neighbor_id,neighbor_when,neighbor_source,neighbor_fields,neighbor_ref in neighboring:
                if (neighbor_id==obs_id or neighbor_source==source or
                    neighbor_ref!=observation_session):
                    continue
                lag=abs((datetime.fromisoformat(neighbor_when)-latest_dt).total_seconds())
                if lag<=15:
                    corroborating.append((neighbor_source,json.loads(neighbor_fields)))
            conflict=set()
            consistent=[]
            for channel,values in corroborating:
                overlap=set(snapshot["fields"]) & set(values)
                different={key for key in overlap if
                           Decimal(snapshot["fields"][key])!=Decimal(values[key])}
                if different:
                    conflict.update(different)
                elif overlap:
                    consistent.append(channel)
            reconciliation={
                "status":("CONFLICT" if conflict else
                          "CROSS_CHECKED_UNVERIFIED" if consistent else
                          "SINGLE_SOURCE_UNVERIFIED"),
                "conflicting_fields":sorted(conflict),
                "corroborating_channels":sorted(set(consistent)),
                "independently_platform_verified":False,
            }
            if conflict and freshness=="CURRENT_UNVERIFIED":
                freshness="CONFLICTED_UNVERIFIED"
        return {
            "domain":scope[0],"account_id":scope[1],
            "platform_id":row[0],"currency":row[1],"display_name":row[2],
            "registered_at":row[3],"session_state":state,
            "local_session_ref_present":bool(session_ref),
            "session_changed_at":session_when,
            "device_id":device_id,
            "freshness":freshness,
            "latest_financial":snapshot,
            "reconciliation":reconciliation,
            "observation_count":count,
            "transactions":[dict(zip(("transaction_id","kind","amount","status",
                              "occurred_at"),x)) for x in transactions],
            "separate_settled_and_pending":True,
            "browser_authenticated_status_unverified":True,
            "session_credentials_held_by_backend":False,
        }


def re_hex(value: str) -> bool:
    return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)
