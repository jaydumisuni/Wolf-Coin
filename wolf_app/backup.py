"""Wolf-Coin native-host-owned SQLite backup/restore.

No browser cookies, private tokens or site credentials are held in this
database. The backup contains sensitive account metadata and MUST be stored
in a private OS app-data location; encryption is a native host obligation.
Never overwrites an existing target. Restoring requires session revalidation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys

from wolf_core.contracts import ContractError
from .contracts import REQUEST_SCHEMA
from .store import ApplicationStore


class BackupRefused(ContractError):
    pass


def _checked_source(source:Path)->None:
    if source.is_symlink() or not source.is_file() or source.stat().st_size<=0:
        raise BackupRefused("backup source must be existing regular nonsymlink file")
    # A read-only meta check must not initialize a missing/foreign database.
    with sqlite3.connect(source.as_uri()+"?mode=ro",uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise BackupRefused("SQLite integrity check failed")
        try:
            v=db.execute("SELECT value FROM app_meta WHERE key='schema'").fetchone()
        except sqlite3.DatabaseError as exc:
            raise BackupRefused("missing Wolf application schema") from exc
        if v is None or v[0] not in ("1","2"):
            raise BackupRefused("unsupported Wolf application backup schema")
        ApplicationStore.verify_audit_connection(db)


def _new_target(target:Path)->None:
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_symlink() or target.exists():
        raise BackupRefused("target exists or is symlink; never overwrite")
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    os.close(fd)


def _consistent_copy(source:Path,target:Path)->None:
    _new_target(target)
    try:
        with sqlite3.connect(str(source),timeout=10) as incoming:
            with sqlite3.connect(str(target),timeout=10) as outgoing:
                incoming.backup(outgoing)
                if outgoing.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                    raise BackupRefused("copy integrity failure")
        if os.name=="posix":
            os.chmod(target,0o600)
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def _read_only_audit_count(path:Path)->int:
    """Validate backup without silently migrating/mutating archival input."""
    with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True) as db:
        return ApplicationStore.verify_audit_connection(db)


def backup(db_path:Path,output:Path)->dict:
    source=Path(db_path)
    destination=Path(output)
    _checked_source(source)
    _consistent_copy(source,destination)
    try:
        _checked_source(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return {
        "schema":"wolf.app.backup-receipt.v1",
        "operation":"BACKUP",
        "file_sha256":sha256(destination.read_bytes()).hexdigest(),
        "size_bytes":destination.stat().st_size,
        "records_checked":_read_only_audit_count(destination),
        "credential_material_present":False,
        "encrypted_by_backend":False,
        "requires_native_host_encryption":True,
        "external_signatures":False,
    }


def restore(backup_file:Path,new_db:Path)->dict:
    source=Path(backup_file)
    destination=Path(new_db)
    _checked_source(source)
    _consistent_copy(source,destination)
    try:
        output=ApplicationStore(destination)
        # Treat restored session as old until the *native host* validates
        # the actual Chromium/WebView browser session.
        restore_id="restore_"+secrets.token_hex(12)
        output.handle({
            "schema":REQUEST_SCHEMA,"request_id":restore_id,
            "operation":"host.startup",
            "payload":{"host_instance_id":restore_id},
        })
        count=output.verify_audit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return {
        "schema":"wolf.app.backup-receipt.v1",
        "operation":"RESTORE",
        "source_sha256":sha256(source.read_bytes()).hexdigest(),
        "restored_db_sha256":sha256(destination.read_bytes()).hexdigest(),
        "records_checked":count,
        "restored_sessions_revalidation_required":True,
        "registered_accounts_preserved":True,
        "old_browser_session_credentials_restored":False,
        "native_host_must_restore_browser_profiles_separately":True,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="wolf-app-backup")
    direction=p.add_mutually_exclusive_group(required=True)
    direction.add_argument("--backup",type=Path)
    direction.add_argument("--restore",type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        value=(backup(args.backup,args.output) if args.backup else
               restore(args.restore,args.output))
        print(json.dumps(value,sort_keys=True))
        return 0
    except (BackupRefused,ContractError,sqlite3.DatabaseError,OSError,ValueError) as exc:
        print(json.dumps({"status":"BLOCKED","error":type(exc).__name__,
                          "operation":"BACKUP_OR_RESTORE"}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
