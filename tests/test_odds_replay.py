"""Wolf-Coin historical lab negative controls and reproducibility."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import csv
from hashlib import sha256
import json

import pytest

from wolf_lab.odds_replay import ReplayRefused, ReplayPolicy, load_season, replay, render_html, EloResearchModel
from wolf_lab.cli import main


HEADERS=("Date","HomeTeam","AwayTeam","FTR","B365H","B365D","B365A")


def season(tmp_path, name, start, *, n=80, quoted=("2.3","3.3","3.5"), outcome="H"):
    path=tmp_path/name
    with path.open("w",newline="",encoding="utf-8") as fp:
        writer=csv.DictWriter(fp,fieldnames=HEADERS)
        writer.writeheader()
        for i in range(n):
            day=start+timedelta(days=i//2)
            writer.writerow({"Date":day.strftime("%d/%m/%Y"),
                             "HomeTeam":f"H{i%11}", "AwayTeam":f"A{i%13}",
                             "FTR":outcome if i%3 else "D", "B365H":quoted[0],
                             "B365D":quoted[1], "B365A":quoted[2]})
    return path,sha256(path.read_bytes()).hexdigest()


def test_realistic_holdout_replays_deterministically(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1))
    b,hb=season(tmp_path,"holdout.csv",date(2024,8,1),outcome="A")
    x=replay(load_season(a,expected_sha256=ha),load_season(b,expected_sha256=hb))
    y=replay(load_season(a,expected_sha256=ha),load_season(b,expected_sha256=hb))
    assert x==y
    assert x["train_matches"]==80 and x["holdout_matches"]==80
    assert x["live_ready"] is False and x["profit_proven"] is False
    assert isinstance(x["net_virtual_ZMW"],str)
    assert len(x["ledger"])==x["bets"]
    assert x["bets"]<=x["holdout_days"]
    for line in x["ledger"]:
        previous = Decimal(line["balance"]) - Decimal(line["net"])
        assert Decimal(line["stake"]) <= previous * Decimal("0.005")
        assert line["day"]>=x["holdout_start"]


def test_no_trading_when_expected_edge_not_present(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1))
    b,hb=season(tmp_path,"holdout.csv",date(2024,8,1))
    policy=ReplayPolicy(min_expected_value=Decimal("0.50"))
    report=replay(load_season(a,expected_sha256=ha),load_season(b,expected_sha256=hb),policy=policy)
    assert report["profit_proven"] is False


def test_data_hash_substitution_refused(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1))
    with pytest.raises(ReplayRefused,match="digest"):
        load_season(a,expected_sha256="0"*64)


def test_overlapping_or_reversed_dates_refused(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1))
    b,hb=season(tmp_path,"holdout.csv",date(2023,8,1),quoted=("2.4","3.3","3.5"))
    with pytest.raises(ReplayRefused,match="chronologically"):
        replay(load_season(a,expected_sha256=ha),load_season(b,expected_sha256=hb))


@pytest.mark.parametrize("price",["0","1","-3","inf","NaN","x"])
def test_bad_bookmaker_quote_refused(tmp_path,price):
    p,h=season(tmp_path,"invalid.csv",date(2023,8,1),quoted=(price,"3","3"))
    with pytest.raises((ReplayRefused,ArithmeticError,ValueError)):
        load_season(p,expected_sha256=h)


def test_duplicate_fixture_identity_refused(tmp_path):
    p,h=season(tmp_path,"dupe.csv",date(2023,8,1))
    with p.open("a",newline="") as fp:
        writer=csv.DictWriter(fp,fieldnames=HEADERS)
        writer.writerow({"Date":"01/08/2023","HomeTeam":"H0","AwayTeam":"A0",
                         "FTR":"H","B365H":"2.3","B365D":"3.3","B365A":"3.5"})
    h=sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ReplayRefused,match="duplicate"):
        load_season(p,expected_sha256=h)


def test_one_day_predictions_not_updated_by_same_day_result(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1))
    dataset=load_season(a,expected_sha256=ha)
    model=EloResearchModel(65.0,20.0,0.27)
    matches=[m for m in dataset.matches if m.day==dataset.matches[0].day]
    p1=[model.prediction(m) for m in matches]
    p2=[model.prediction(m) for m in matches]
    assert p1==p2
    model.learn_after_day(matches)
    assert model.ratings


def test_cli_creates_private_static_report_and_refuses_overwrite(tmp_path,capsys):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1))
    b,hb=season(tmp_path,"holdout.csv",date(2024,8,1))
    output=tmp_path/"research"/"metrics.json"
    html=tmp_path/"research"/"dashboard.html"
    argv=["--train",str(a),"--holdout",str(b),"--train-sha256",ha,"--holdout-sha256",hb,
          "--report-json",str(output),"--report-html",str(html)]
    assert main(argv)==0
    summary=json.loads(capsys.readouterr().out)
    assert summary["live_ready"] is False
    assert output.stat().st_mode & 0o777 == 0o600
    assert html.stat().st_mode & 0o777 == 0o600
    assert "PAPER ONLY" in html.read_text()
    assert main(argv)==2
    assert json.loads(capsys.readouterr().err)["status"]=="BLOCKED"


def test_no_html_injection_from_team_name(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1))
    b,hb=season(tmp_path,"holdout.csv",date(2024,8,1))
    report=replay(load_season(a,expected_sha256=ha),load_season(b,expected_sha256=hb))
    fake=dict(report)
    fake["ledger"]=[{"day":"2024-01-01","fixture":"<script>alert(1)</script>",
                    "pick":"H","actual":"D","odds":"3","stake":"0.5","net":"-0.5","balance":"99.5"}]
    html=render_html(fake)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_replay_stays_paper_only_even_on_claimed_positive_return(tmp_path):
    a,ha=season(tmp_path,"train.csv",date(2023,8,1),quoted=("6","6","6"))
    b,hb=season(tmp_path,"holdout.csv",date(2024,8,1),quoted=("6","6","6"))
    report=replay(load_season(a,expected_sha256=ha),load_season(b,expected_sha256=hb))
    assert report["profit_proven"] is False
    assert report["live_ready"] is False
