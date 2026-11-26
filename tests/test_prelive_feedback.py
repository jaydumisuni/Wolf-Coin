"""Negative proofs for outcome ordering, immutable receipts, loss learning."""
from dataclasses import replace
from datetime import date,timedelta
from decimal import Decimal
import copy
import json
import pytest

from wolf_lab.odds_replay import OddsMatch,OddsSeason,ReplayRefused
from wolf_lab import prelive_feedback as f


def trained():
    matches = []
    start = date(2022,1,1)
    names = ("A","B","C","D","E","F")
    for i in range(310):
        day = start+timedelta(days=i)
        h=names[i%6];a=names[(i+1+(i//6)%4)%6]
        if a==h:a=names[(i+2)%6]
        outcome=("H","A","D")[i%3]
        matches.append(OddsMatch(day,h,a,outcome,
                                 (Decimal("3.0"),Decimal("4.0"),Decimal("3.0"))))
    return OddsSeason(tuple(matches),"a"*64,"synthetic-prior")


def one_offer(day=date(2023,6,1)):
    return f.PreMatchOffer(day,"HomeClub","AwayClub",
                          (Decimal("3.0"),Decimal("4.0"),Decimal("3.0")))


def settle_with_loss(engine,day=date(2023,6,1)):
    offer=one_offer(day)
    prepared=engine.prepare_day([offer])
    shadow=prepared["paper_decision"]
    assert shadow is not None
    predicted = ("H","D","A")[max(range(3),key=lambda i: prepared["predictions"][0]["adaptive"][i])]
    # A lost paper pick and an incorrect maximum-probability forecast are
    # different failure classes. Choose an outcome outside both for this test.
    losing=next(o for o in ("H","D","A") if o not in (shadow["selection"],predicted))
    receipt=f.SettledResult(offer.identity,losing,day+timedelta(days=1),"b"*64)
    return prepared,receipt


def test_loss_updates_only_after_sealed_later_settlement():
    engine=f.PreliveFeedback(trained(),"b"*64)
    initial=f._state_sha(engine.model)
    control=f._state_sha(engine.control)
    fixture=f.OddsMatch(date(2023,6,2),"HomeClub","AwayClub","D",one_offer().prices)
    next_before=engine.model.prediction(fixture)
    before,receipt=settle_with_loss(engine)
    assert f._state_sha(engine.model)==initial
    assert engine.wagers==[]
    result=engine.settle_day([receipt])
    assert not result["paper"]["won"]
    assert Decimal(result["paper"]["virtual_net_ZMW"])<0
    assert f._state_sha(engine.model)!=initial
    next_after=engine.model.prediction(fixture)
    assert any(abs(next_after[x]-next_before[x])>1e-9 for x in f.OUTCOMES),         "loss settlement must alter a future forecast"
    assert f._state_sha(engine.control)==control
    assert engine.loss_day_updates==1
    assert engine.forecast_errors==1
    assert engine.report()["paper_losses"]==1
    assert engine.report()["paper_wins"]==0
    assert f.verify_journal(engine.journal)==engine.report()["journal_head_sha256"]
    assert engine.journal[0]["kind"]=="predictions_frozen_before_outcomes"
    assert engine.journal[1]["kind"]=="settled_then_updated"
    assert before["predictions"][0]["identity"]==receipt.identity
    assert engine.report()["execution_authority"] is False
    with pytest.raises(ReplayRefused,match="before prediction"):
        engine.settle_day([receipt])
    with pytest.raises(ReplayRefused,match="increase"):
        engine.prepare_day([one_offer()])


@pytest.mark.parametrize("fault",["wrong_id","early","wrong_digest","missing","duplicated","bad_result"])
def test_bad_settlement_does_not_train_or_change_bankroll(fault):
    engine=f.PreliveFeedback(trained(),"b"*64)
    pre,receipt=settle_with_loss(engine)
    initial=f._state_sha(engine.model)
    bankroll=engine.bankroll
    if fault=="wrong_id":bad=[replace(receipt,identity="2023-06-01|Bogus|Unknown")]
    elif fault=="early":bad=[replace(receipt,observed_day=one_offer().day)]
    elif fault=="wrong_digest":bad=[replace(receipt,source_sha256="c"*64)]
    elif fault=="missing":bad=[]
    elif fault=="duplicated":bad=[receipt,receipt]
    else:
        with pytest.raises(ReplayRefused,match="final result"):
            f.SettledResult(receipt.identity,"CORRUPT",receipt.observed_day,receipt.source_sha256)
        return
    with pytest.raises(ReplayRefused):
        engine.settle_day(bad)
    assert f._state_sha(engine.model)==initial
    assert engine.bankroll==bankroll
    assert len(engine.journal)==1 and engine.pending is not None
    engine.settle_day([receipt])
    assert len(engine.journal)==2


def test_no_pre_outcome_unsealed_cross_day_or_duplicate_offers():
    engine=f.PreliveFeedback(trained(),"b"*64)
    with pytest.raises(ReplayRefused,match="before prediction"):
        engine.settle_day([])
    with pytest.raises(ReplayRefused,match="increase"):
        engine.prepare_day([one_offer(date(2022,6,1))])
    with pytest.raises(ReplayRefused,match="duplicate"):
        engine.prepare_day([one_offer(),one_offer()])
    with pytest.raises(ReplayRefused,match="increase"):
        engine.prepare_day([one_offer(),one_offer(date(2023,6,2))])
    engine.prepare_day([one_offer()])
    with pytest.raises(ReplayRefused,match="settle"):
        engine.prepare_day([one_offer(date(2023,6,2))])


def test_journal_rejects_tampering_reordering_and_deleted_entries():
    engine=f.PreliveFeedback(trained(),"b"*64)
    _,receipt=settle_with_loss(engine)
    engine.settle_day([receipt])
    clean=copy.deepcopy(engine.journal)
    tampered=copy.deepcopy(clean)
    tampered[1]["body"]["paper"]["won"]=True
    with pytest.raises(ReplayRefused,match="hash"):
        f.verify_journal(tampered)
    with pytest.raises(ReplayRefused):
        f.verify_journal(list(reversed(clean)))
    with pytest.raises(ReplayRefused):
        f.verify_journal(clean[1:])
    assert f.verify_journal(clean)==clean[-1]["entry_sha256"]


def test_pre_match_offers_have_no_outcome_field():
    o=one_offer()
    assert "result" not in vars(o) and "outcome" not in vars(o)
    with pytest.raises(TypeError):
        f.PreMatchOffer(o.day,o.home,o.away,o.prices,"H")
    with pytest.raises(ReplayRefused):
        f.PreMatchOffer(o.day,o.home,o.away,(Decimal("0"),Decimal("2"),Decimal("4")))


def test_historical_output_fail_closed_and_no_live_authority(tmp_path,monkeypatch):
    seasons={}
    for k in ("2022-23","2023-24","2024-25","2025-26"):
        season_number=int(k[:4])
        matches=[]
        for i in range(300):
            day=date(season_number,8,1)+timedelta(days=i)
            home=f"C{i%20}";away=f"C{(i+1)%20}"
            matches.append(OddsMatch(day,home,away,("H","D","A")[i%3],
                                      (Decimal("2.05"),Decimal("3.3"),Decimal("4.1"))))
        digest=str(season_number)*16
        seasons[k]=OddsSeason(tuple(matches),digest,k)
    monkeypatch.setattr(f,"SOURCES",{k:v.digest for k,v in seasons.items()})
    report,journals=f.retrospective_review(seasons)
    assert len(journals)==3
    assert all(len(x["entries"])==600 for x in journals)
    assert f.verify_retrospective_evidence(report,journals)
    forged_report=copy.deepcopy(report)
    forged_report["folds"][0]["market_brier"]+=0.10
    with pytest.raises(ReplayRefused,match="Brier"):
        f.verify_retrospective_evidence(forged_report,journals)
    forged_journals=copy.deepcopy(journals)
    forged_journals[0]["entries"][0]["body"]["predictions"][0]["adaptive"][0]+=0.2
    with pytest.raises(ReplayRefused,match="hash"):
        f.verify_retrospective_evidence(report,forged_journals)
    assert report["consistent_predictive_superiority_proven"] is False
    assert report["live_admission"] is False
    assert report["independent_settlement_receipts"] is False
    assert len(report["pooled_95pct_day_cluster_bootstrap_market_minus_adaptive"])==2
    for journal in journals:
        f.verify_journal(journal["entries"])
    with pytest.raises(ReplayRefused,match="source SHA256"):
        f.retrospective_review({**seasons,"2025-26":replace(
            seasons["2025-26"],digest="e"*64)})
