from pathlib import Path
from contextlib import closing
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen
import json
import pytest
import subprocess
import os
import sys

from wolf_core.contracts import AccountScope, Domain
from wolf_core.ledger import EventLedger
from wolf_core.bankroll import PaperBankroll
from wolf_gateway.resident import instance_lock, ResidentBlocked, verify_paper_state, main
from wolf_gateway.dashboard import handler


def test_uninitialized_never_created(tmp_path):
    missing=tmp_path / 'missing.db'
    assert main(['--db', str(missing), '--check']) == 2
    assert not missing.exists()
    assert not (tmp_path/'missing.db.resident.lock').exists()


def test_bad_data_blocked(tmp_path):
    db=tmp_path/'bad.db'
    db.write_bytes(b'not sqlite')
    with pytest.raises(ResidentBlocked):
        verify_paper_state(db)


def test_single_instance_lock(tmp_path):
    db=tmp_path/'paper.db'
    PaperBankroll(EventLedger(db)).create(AccountScope(Domain.SPORTS,'pilot-1'))
    with instance_lock(db) as path:
        assert path == db.resolve()
        with pytest.raises(ResidentBlocked, match='another resident'):
            with instance_lock(db):
                pytest.fail('duplicate resident acquired lock')
    with instance_lock(db):
        assert True


def test_symlink_lock_denied(tmp_path):
    db=tmp_path/'paper.db'
    PaperBankroll(EventLedger(db)).create(AccountScope(Domain.SPORTS,'pilot-1'))
    other=tmp_path/'forbidden'
    other.write_text('unaltered')
    (tmp_path/'paper.db.resident.lock').symlink_to(other)
    with pytest.raises(OSError):
        with instance_lock(db):
            pytest.fail('accepted symlink as lock')
    assert other.read_text()=='unaltered'


def test_readonly_two_tab_runtime(tmp_path):
    db=tmp_path/'paper.db'
    b=PaperBankroll(EventLedger(db))
    for domain in (Domain.SPORTS,Domain.TRADING):
        a=AccountScope(domain,'pilot-1')
        b.create(a)
        b.add_paper_funds(a, amount='100', event_id='virtual-100')
    with instance_lock(db):
        with ThreadingHTTPServer(('127.0.0.1',0), handler(db,'pilot-1')) as server:
            t=Thread(target=server.serve_forever,daemon=True);t.start()
            try:
                for path in ('sports','trading'):
                    with urlopen(f'http://127.0.0.1:{server.server_port}/{path}',timeout=3) as response:
                        html=response.read().decode()
                        assert 'NO LIVE EXECUTION' in html
                        assert '100' in html
            finally:
                server.shutdown(); t.join(3)
    assert verify_paper_state(db)['status']=='RESEARCH_ONLY'


def test_released_after_subprocess_termination(tmp_path):
    db=tmp_path/'paper.db'
    PaperBankroll(EventLedger(db)).create(AccountScope(Domain.TRADING,'pilot-1'))
    source='''import time,sys
from pathlib import Path
from wolf_gateway.resident import instance_lock
with instance_lock(Path(sys.argv[1])):
 print('LOCKED',flush=True)
 time.sleep(90)
'''
    env=dict(os.environ)
    env['PYTHONPATH']=os.getcwd()
    proc=subprocess.Popen([sys.executable,'-c',source,str(db)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
        assert proc.stdout.readline().strip()=='LOCKED'
        with pytest.raises(ResidentBlocked):
            with instance_lock(db):
                pass
        proc.terminate()
        proc.wait(timeout=5)
        with instance_lock(db):
            assert True
    finally:
        if proc.poll() is None:
            proc.kill();proc.wait(timeout=5)
