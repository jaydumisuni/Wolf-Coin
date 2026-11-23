import json
from pathlib import Path

from wolf_core.paper_operator import run
from wolf_core.cli import doctor


def test_virtual_two_account_flow(tmp_path: Path, capsys):
    db = tmp_path / 'state' / 'paper.db'
    def call(domain, op, *args):
        assert run(['--db', str(db), '--domain', domain, '--account', 'one', op, *args]) == 0
        return json.loads(capsys.readouterr().out)
    a = call('sports', 'init')
    b = call('trading', 'init')
    assert a['live_enabled'] is False and b['real_money_effects'] is False
    assert call('sports', 'deposit', '--amount', '100', '--event-id', 'start')['virtual_balance'] == '100'
    assert call('trading', 'deposit', '--amount', '100', '--event-id', 'start')['virtual_balance'] == '100'
    assert call('sports', 'deposit', '--amount', '100', '--event-id', 'start')['virtual_balance'] == '100'
    assert call('sports', 'withdraw', '--amount', '40', '--event-id', 'withdraw')['virtual_balance'] == '60'
    assert call('trading', 'status')['virtual_balance'] == '100'
    assert call('sports', 'freeze', '--status', 'FROZEN', '--event-id', 'freeze')['account_status'] == 'FROZEN'
    assert doctor(db)['status'] == 'RESEARCH_ONLY'


def test_read_only_manual_odds_no_bet_or_source_rights(tmp_path, capsys):
    db = tmp_path / 'does-not-exist.db'
    assert run(['--db', str(db), 'odds', '--home', '2', '--draw', '3.5', '--away', '4']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['verdict'] == 'NO_EXECUTION'
    assert result['source_rights_confirmed'] is False
    assert abs(sum(map(float, result['implied_no_vig'].values())) - 1) < 1e-12
    assert not db.exists()


def test_operator_refuses_bad_inputs_and_uninitialized(tmp_path, capsys):
    db = tmp_path / 'virtual.db'
    pre = ['--db', str(db), '--domain', 'sports', '--account', 'one']
    assert run(pre + ['status']) == 2
    assert not db.exists()
    assert run(pre + ['init']) == 0
    capsys.readouterr()
    assert run(pre + ['deposit', '--amount', 'NaN', '--event-id', 'bad']) == 2
    assert run(pre + ['deposit', '--amount', '100', '--event-id', 'one']) == 0
    capsys.readouterr()
    assert run(pre + ['deposit', '--amount', '200', '--event-id', 'one']) == 2
    assert run(pre + ['withdraw', '--amount', '101', '--event-id', 'too-much']) == 2
    assert run(pre + ['freeze', '--status', 'HALT', '--event-id', 'halt']) == 0
    assert run(pre + ['freeze', '--status', 'FROZEN', '--event-id', 'downgrade']) == 2
    assert run(pre + ['odds', '--home', '1', '--draw', '2', '--away', '3']) == 2

def test_corrupt_paper_database_fails_with_bounded_error(tmp_path, capsys):
    path=tmp_path/'garbled.db'
    path.write_bytes(b'not a sqlite database')
    assert run(['--db',str(path),'status']) == 2
    assert json.loads(capsys.readouterr().err)['status']=='BLOCKED'
