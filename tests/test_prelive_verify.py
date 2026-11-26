"""Independent verifier must reject tampered and mislabeled learning journals."""
from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy

import pytest

from wolf_lab.prelive_verify import verify
from wolf_lab.loss_feedback import FeedbackError


def test_real_source_bound_report_verifies_on_kratos():
    folder=Path("/home/kratos/projects/Wolf-Coin/.workspace/research/prelive-loss-feedback-20261126-frozen-7448515")
    if not folder.is_dir():
        pytest.skip("private immutable research evidence not present on this host")
    summary=verify(folder)
    assert summary["status"]=="MECHANISM_VERIFIED"
    assert summary["folds_checked"]==4
    assert summary["settled_forecasts_checked"]==1520
    assert summary["losing_settlements_checked"]==736
    assert summary["adaptive_promotion"]=="REJECT_KEEP_FROZEN"
    assert not summary["live_money_authorized"]


def test_changed_journal_manifest_rejected_without_executing(tmp_path):
    root=Path("/home/kratos/projects/Wolf-Coin/.workspace/research/prelive-loss-feedback-20261126-frozen-7448515")
    if not root.is_dir():
        pytest.skip("source-bound private evidence not present")
    for f in root.iterdir():
        if f.is_file():
            (tmp_path/f.name).write_bytes(f.read_bytes())
    j=tmp_path/"journal-2021-22.json"
    data=json.loads(j.read_text())
    data["events"][0]["data"]["probabilities"][0]=0.9
    j.write_text(json.dumps(data))
    with pytest.raises(FeedbackError,match="journal artifact SHA-256 mismatch"):
        verify(tmp_path)


def test_recomputed_score_forgery_rejected(tmp_path):
    root=Path("/home/kratos/projects/Wolf-Coin/.workspace/research/prelive-loss-feedback-20261126-frozen-7448515")
    if not root.is_dir():
        pytest.skip("source-bound private evidence not present")
    for f in root.iterdir():
        if f.is_file():
            (tmp_path/f.name).write_bytes(f.read_bytes())
    p=tmp_path/"qualification.json"
    data=json.loads(p.read_text())
    data["seasons"][0]["adaptive"]["brier"]=0.1
    from wolf_lab.loss_feedback import _digest
    data.pop("seal_sha256")
    data["seal_sha256"]=_digest(data)
    p.write_text(json.dumps(data))
    with pytest.raises(FeedbackError,match="proper scores"):
        verify(tmp_path)
