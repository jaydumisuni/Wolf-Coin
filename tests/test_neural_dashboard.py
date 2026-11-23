"""CC0 neural research HTML is never a provider or execution surface."""
from __future__ import annotations
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json
import pytest
from wolf_gateway.dashboard import neural_page,handler
from wolf_core.paper_operator import run


def fixture():
    return {
        "schema":"wolf.cc0-neural-public-summary.v1",
        "live_enabled":False,"financial_edge_proven":False,
        "train_rows":2660,"training_rows":2660,"validation_rows":380,
        "validation_class_prior_brier":0.655478614,
        "validation_linear_brier":0.623560457,
        "validation_neural_brier":0.623347533,
        "holdout_scored_matches":45,
        "holdout_unscored_matches":335,
        "holdout_class_prior_brier":0.657353561,
        "holdout_neural_brier":0.611911853,
        "holdout_brier_gain_interval":[-0.050237688,0.15839945],
        "sup_director_stage":"AWAIT_CAPABILITY_SNAPSHOT",
        "historical_score_crosscheck_count":760,
        "historical_score_crosscheck_conflicts":0,
        "model_frozen_digest":"sha256:"+"a"*64
    }


def test_neural_evidence_is_explicit_about_uncertainty(tmp_path):
    f=tmp_path/"neural-summary.json"
    f.write_text(json.dumps(fixture()))
    html=neural_page(f).decode()
    assert "0.655478614" in html and "0.623347533" in html
    assert "0.611911853" in html
    assert "INTERVAL CROSSES ZERO" in html
    assert "AWAIT_CAPABILITY_SNAPSHOT" in html
    assert "NO FUNDS" in html


@pytest.mark.parametrize("change",[
    {"live_enabled":True},
    {"financial_edge_proven":True},
    {"schema":"fake.security.elevated"},
])
def test_forged_liveness_or_schema_fails_closed(tmp_path,change):
    f=tmp_path/"fake.json"
    value=fixture();value.update(change);f.write_text(json.dumps(value))
    html=neural_page(f).decode()
    assert "evidence unavailable" in html
    assert "NO FUNDS" in html


def test_neural_html_escapes_json_values(tmp_path):
    f=tmp_path/"unsafe.json"
    val=fixture();val["sup_director_stage"]="<script>not-allowed</script>"
    f.write_text(json.dumps(val))
    html=neural_page(f).decode()
    assert "<script>not-allowed</script>" not in html
    assert "&lt;script&gt;" in html


def test_http_neural_is_read_only_and_coexists_with_paper_views(tmp_path):
    db=tmp_path/"paper.sqlite3"
    assert run(["--db",str(db),"init"])==0
    proof=tmp_path/"neural.json"
    proof.write_text(json.dumps(fixture()))
    server=ThreadingHTTPServer(("127.0.0.1",0),handler(db,"pilot-1",neural_report=proof))
    t=Thread(target=server.serve_forever,daemon=True);t.start()
    try:
        root=f"http://127.0.0.1:{server.server_port}"
        for path in ("/neural","/sports","/trading","/health"):
            with urlopen(root+path,timeout=5) as response:
                assert response.status==200
                if path=="/neural":
                    html=response.read().decode()
                    assert "0.611911853" in html
                    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
        with pytest.raises(HTTPError) as error:
            urlopen(Request(root+"/neural",method="POST"),timeout=5)
        assert error.value.code==405
    finally:
        server.shutdown();server.server_close();t.join(timeout=4)


def test_typed_cpu_candidate_does_not_claim_sup_or_formula_admission(tmp_path):
    value=fixture()
    value.update({
        "typed_route_training":"PRODUCT_OWNED_CPU_TRAINING_REPRODUCED",
        "typed_route_verifier":"NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY",
        "typed_route_prediction_rows":45,
        "typed_route_max_absolute_error":7.732148255001903e-13,
        "typed_route_sup_admitted":False,
        "typed_route_formula_certificate":False,
    })
    p=tmp_path/"review.json"
    p.write_text(json.dumps(value))
    text=neural_page(p).decode()
    assert "Typed CPU research route" in text
    assert "NOT ADMITTED BY SUP OR FORMULA" in text
    assert "WOLF-COIN-OWNED CANDIDATE" in text
    assert "NO FUNDS" in text


def test_forged_typed_cpu_promotion_is_not_displayed_as_qualified(tmp_path):
    value=fixture()
    value.update({
        "typed_route_training":"PRODUCT_OWNED_CPU_TRAINING_REPRODUCED",
        "typed_route_verifier":"NUMERICAL_REPLAY_PASS_CANDIDATE_ONLY",
        "typed_route_prediction_rows":45,
        "typed_route_sup_admitted":True,
        "typed_route_formula_certificate":True,
    })
    p=tmp_path/"fake.json"
    p.write_text(json.dumps(value))
    text=neural_page(p).decode()
    assert "Typed CPU research route" not in text
    assert "NO FUNDS" in text
