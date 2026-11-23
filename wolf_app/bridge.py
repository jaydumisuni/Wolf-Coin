"""Portable newline JSON IPC for native Wolf-Coin hosts.

One request per line, one response per line. No HTTP listener, no origin
bypass, no website credentials, no network and no live actions. The desktop/
Android host must protect the child process and authenticate its own bridge.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import sys

from wolf_core.contracts import ContractError
from .contracts import MAX_MESSAGE, ident, parse_request, response
from .store import AppConflict, ApplicationStore


def _parse(raw: str) -> dict:
    if len(raw.encode("utf-8")) > MAX_MESSAGE:
        raise ContractError("IPC message too large")
    def no_duplicates(pairs):
        d={}
        for key,value in pairs:
            if key in d:
                raise ContractError("duplicate IPC JSON field")
            d[key]=value
        return d
    try:
        document=json.loads(
            raw,object_pairs_hook=no_duplicates,
            parse_constant=lambda _: (_ for _ in ()).throw(ContractError("nonfinite JSON"))
        )
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ContractError("invalid JSON request") from exc
    if not isinstance(document,dict):
        raise ContractError("top-level IPC object required")
    return document


def _read_native_key(path:Path)->bytes:
    if path.is_symlink() or not path.is_file():
        raise ContractError("native IPC key must be an existing regular nonsymlink file")
    if os.name=="posix" and stat.S_IMODE(path.stat().st_mode)!=0o600:
        raise ContractError("native IPC key must have owner-only 0600 permissions")
    value=path.read_bytes()
    if len(value)!=32:
        raise ContractError("native IPC key must be 32 random bytes")
    return value


def _initialize_native_key(path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(secrets.token_bytes(32))
        f.flush()
        os.fsync(f.fileno())


def _authenticate(document:dict,key:bytes)->None:
    supplied=document.get("auth_tag")
    if not isinstance(supplied,str):
        raise ContractError("signed native host request required")
    original={name:value for name,value in document.items() if name!="auth_tag"}
    raw=json.dumps(original,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
    calculated=hmac.new(key,raw.encode("utf-8"),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated,supplied):
        raise ContractError("native IPC authentication rejected")


def process(store:ApplicationStore,raw:str,*,key:bytes|None=None)->dict:
    request_id="invalid"
    try:
        value=_parse(raw)
        if key is not None:
            _authenticate(value,key)
        if isinstance(value.get("request_id"),str):
            try:
                request_id=ident(value["request_id"],"request ID")
            except ContractError:
                pass
        return store.handle(value)
    except (ContractError,AppConflict,sqlite3.DatabaseError,OSError,
            ValueError,TypeError,KeyError) as exc:
        return response(request_id,"REJECTED",{
            "error":type(exc).__name__,
            "message":"Rejected by versioned bridge contract or local state",
            "requires_user_action":False,
        })


def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="wolf-app-bridge",
        description="Wolf-Coin native IPC for contextual browser and financial workflows")
    p.add_argument("--db",type=Path)
    p.add_argument("--once",help="one JSON request string instead of stdin loop")
    p.add_argument("--verify-audit",action="store_true")
    p.add_argument("--key-file",type=Path,
                   help="native host-owned 0600 file with 32 random secret bytes")
    p.add_argument("--init-key",type=Path,
                   help="atomically create the native host IPC key once; never print secret")
    args=p.parse_args(argv)
    try:
        if args.init_key:
            if args.key_file or args.once or args.verify_audit or args.db:
                raise ContractError("key initialization cannot be combined with bridge operation")
            _initialize_native_key(args.init_key)
            print(json.dumps({"status":"NATIVE_IPC_KEY_CREATED",
                 "key_material_printed":False}))
            return 0
        if not args.db:
            raise ContractError("--db required")
        if not args.key_file:
            raise ContractError("native host key required for signed application IPC")
        key=_read_native_key(args.key_file)
        store=ApplicationStore(args.db)
        if args.verify_audit:
            print(json.dumps({"schema":"wolf.app.audit-check.v1",
                "records_checked":store.verify_audit(),"externally_signed":False},sort_keys=True))
            return 0
        if args.once is not None:
            print(json.dumps(process(store,args.once,key=key),sort_keys=True))
            return 0
        for line in sys.stdin:
            result=process(store,line,key=key)
            print(json.dumps(result,sort_keys=True),flush=True)
        return 0
    except (ContractError,sqlite3.DatabaseError,OSError,AppConflict) as exc:
        print(json.dumps({"status":"BLOCKED","error":type(exc).__name__,
                          "reason":"INVALID_NATIVE_BRIDGE_STATE"}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
