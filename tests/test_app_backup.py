"""Backup/restore is create-only, consistent, private, and host-revalidated."""
from __future__ import annotations

from pathlib import Path
import os, sqlite3

import pytest

from wolf_app.backup import backup,restore,BackupRefused
from wolf_app.store import ApplicationStore
from wolf_app.contracts import REQUEST_SCHEMA


def req(i,operation,payload):
    return {"schema":REQUEST_SCHEMA,"request_id":i,
            "operation":operation,"payload":payload}


def seed(db):
    app=ApplicationStore(db)
    assert app.handle(req("r1","account.register",{
        "domain":"sports","account_id":"a","platform_id":"p",
        "currency":"ZMW","display_name":"Test"}))["status"]=="OK"
    from datetime import datetime,timezone
    now=datetime.now(timezone.utc).isoformat()
    app.handle(req("s1","session.record",{
        "domain":"sports","account_id":"a","state":"ACTIVE",
        "session_ref":"local_host_tab","observed_at":now}))
    assert app.verify_audit()==2
    return app


def test_backup_restores_accounts_but_requires_login_revalidation(tmp_path):
    original=tmp_path/"orig.sqlite3"
    app=seed(original)
    archival=tmp_path/"backup.sqlite3"
    saved=backup(original,archival)
    assert saved["operation"]=="BACKUP"
    assert saved["records_checked"]==2
    assert saved["encrypted_by_backend"] is False
    assert saved["requires_native_host_encryption"] is True
    restored=tmp_path/"restored.sqlite3"
    receipt=restore(archival,restored)
    assert receipt["operation"]=="RESTORE"
    assert receipt["restored_sessions_revalidation_required"] is True
    assert receipt["old_browser_session_credentials_restored"] is False
    reloaded=ApplicationStore(restored)
    assert reloaded.verify_audit()==3
    account=reloaded.handle(req("list","accounts.list",{}))["data"]["accounts"][0]
    assert account["display_name"]=="Test"
    assert account["session_state"]=="PAUSED"
    assert account["local_session_ref_present"]
    if os.name=="posix":
        assert archival.stat().st_mode & 0o777==0o600
        assert restored.stat().st_mode & 0o777==0o600


def test_backup_and_restore_never_overwrite_existing_paths(tmp_path):
    db=tmp_path/"orig.sqlite3"
    seed(db)
    backup_file=tmp_path/"archival.sqlite3"
    backup(db,backup_file)
    with pytest.raises(BackupRefused,match="target exists"):
        backup(db,backup_file)
    with pytest.raises(BackupRefused,match="target exists"):
        restore(backup_file,db)
    assert ApplicationStore(db).verify_audit()==2


def test_backup_rejects_corrupt_audit_chain_and_foreign_sqlite(tmp_path):
    db=tmp_path/"orig.sqlite3"
    seed(db)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE app_audit SET record_sha256='forged' WHERE seq=1")
    with pytest.raises(Exception,match="audit"):
        backup(db,tmp_path/"no_output.sqlite3")
    assert not (tmp_path/"no_output.sqlite3").exists()
    foreign=tmp_path/"other.sqlite3"
    with sqlite3.connect(foreign) as conn:
        conn.execute("CREATE TABLE foreign_test (id INTEGER)")
    with pytest.raises(BackupRefused,match="missing Wolf application schema"):
        restore(foreign,tmp_path/"not_created.sqlite3")
    assert not (tmp_path/"not_created.sqlite3").exists()


def test_backup_symlink_source_or_target_rejected(tmp_path):
    db=tmp_path/"orig.sqlite3"
    seed(db)
    link=tmp_path/"link"
    link.symlink_to(db)
    with pytest.raises(BackupRefused):
        backup(link,tmp_path/"nope.sqlite3")
    target=tmp_path/"target"
    target.symlink_to(db)
    with pytest.raises(BackupRefused):
        backup(db,target)
