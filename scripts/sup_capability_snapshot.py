"""Wolf-Coin SUP capability-snapshot audit (read-only, no training).

Reuses the existing SUP Director and SUP_SIM; does NOT create a parallel
simulation engine. Binds frozen project generations to independently present
Git commit objects. Distinguishes frozen-pin currentness from latest HEAD.

The public Soup donor is explicitly NOT a proved tabular 1X2 trainer. Hardware
fit from a small NumPy MLP is NOT transferred to its LLM-training methods.
As a result, no method can be marked qualified merely to advance SUP.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any


class SnapshotRefused(ValueError):
    pass


def _run(*argv: str, timeout: int = 12) -> str:
    p = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
    if p.returncode != 0:
        raise SnapshotRefused(f"evidence command failed: {argv[0]} {argv[1] if len(argv)>1 else ''}: {p.stderr[:300]}")
    return p.stdout.strip()


def _commit(repo: Path, pinned: str, owner: str) -> dict[str, Any]:
    if len(pinned) != 40 or any(c not in "0123456789abcdef" for c in pinned):
        raise SnapshotRefused("unqualified frozen git commit")
    kind=_run("git","-C",str(repo),"cat-file","-t",pinned)
    if kind!="commit":
        raise SnapshotRefused(f"{owner}: frozen binding not a git commit")
    observed=_run("git","-C",str(repo),"rev-parse",pinned+"^{commit}")
    if observed!=pinned:
        raise SnapshotRefused(f"{owner}: pinned commit mismatch")
    active=_run("git","-C",str(repo),"rev-parse","HEAD")
    return {
       "owner":owner,
       "frozen_commit":pinned,
       "frozen_commit_object_present":True,
       "observed_pinned_generation":observed,
       "active_checkout_head":active,
       "active_head_equals_frozen_pin":active==pinned,
       "evidence_ref":f"git:{repo}@{pinned}"
    }


def build(request:dict, *, sup_root:Path, cookpit:Path, formula:Path,
          srg:Path, simulation:Path, resource_report:Path,
          soup_remote:str="jaydumisuni/Soup") -> tuple[dict,dict]:
    # This is only a tool for the existing native SUP project. Its public
    # interface is not a replacement for independently signed authority.
    from sup_control.bindings import (
        COOKPIT_REF,FORMULA_REF,SRG_REF,SOUP_REF,SOUP_REALIZE_METHODS,
        SIMULATION_GENERATION,SIMULATION_REVIEWED_SOURCE,
        SIMULATION_EVIDENCE_COMMIT,
    )
    from sup_control.generation import build_sup_generation

    if request.get("target_product")!="Wolf-Coin":
        raise SnapshotRefused("not Wolf-Coin source-bound intake")
    generation=build_sup_generation(sup_root)["id"]
    if request.get("sup_generation")!=generation:
        raise SnapshotRefused("SUP source generation changed; rebuild intake")
    package=request.get("learning_package")
    if not isinstance(package,dict) or package.get("source_product")!="Wolf-Coin":
        raise SnapshotRefused("unqualified cross-product source")
    receipt=request.get("source_qualification")
    if not isinstance(receipt,dict) or receipt.get("independent_human_signature") is not False:
        raise SnapshotRefused("missing explicit unsigned research-only receipt boundary")
    if request.get("sim_request") is not None:
        raise SnapshotRefused("already attached SIM input requires independent reconciliation")

    owner_evidence={
      "cookpit":_commit(cookpit,COOKPIT_REF,"cookpit"),
      "formula":_commit(formula,FORMULA_REF,"formula"),
      "srg":_commit(srg,SRG_REF,"srg"),
      "ttg_simulation_reviewed_source":_commit(
          simulation,SIMULATION_REVIEWED_SOURCE,"ttg-simulation"),
      "ttg_simulation_evidence":_commit(
          simulation,SIMULATION_EVIDENCE_COMMIT,"ttg-simulation-evidence")
    }
    archived=(sup_root/"docs/DONOR_BINDINGS.md").read_text(encoding="utf-8")
    if SOUP_REF not in archived or SIMULATION_GENERATION not in archived:
        raise SnapshotRefused("canonical SUP donor/simulation binding record has drifted")
    # Verifies the existing user-owned fork actually has this git commit.
    remote_sha=_run("gh","api",f"repos/{soup_remote}/git/commits/{SOUP_REF}",
                    "--jq",".sha",timeout=18)
    if remote_sha!=SOUP_REF:
        raise SnapshotRefused("Soup remote donor ref could not be authenticated")
    resources=json.loads(resource_report.read_text(encoding="utf-8"))
    if (resources.get("schema")!="wolf.sup-bit-readonly-resource-evidence.v1"
        or resources.get("research_only") is not True
        or resources.get("actual_neural_model_trained") is not False
        or resources.get("estimate_only") is not True):
        raise SnapshotRefused("resource estimate cannot be used as training approval")
    budget=resources.get("declared_requirements",{})
    if not isinstance(budget,dict) or resources.get("plan_status")!="FIT":
        raise SnapshotRefused("missing conservative CPU resource estimate")

    binding={
      "cookpit_binding":{"source":"cookpit",
        "expected_generation":COOKPIT_REF,
        "observed_generation":owner_evidence["cookpit"]["observed_pinned_generation"],
        "evidence_ref":owner_evidence["cookpit"]["evidence_ref"]},
      "formula_binding":{"source":"formula",
        "expected_generation":FORMULA_REF,
        "observed_generation":owner_evidence["formula"]["observed_pinned_generation"],
        "evidence_ref":owner_evidence["formula"]["evidence_ref"]},
      "srg_binding":{"source":"srg",
        "expected_generation":SRG_REF,
        "observed_generation":owner_evidence["srg"]["observed_pinned_generation"],
        "evidence_ref":owner_evidence["srg"]["evidence_ref"]},
      "simulation_binding":{"source":"ttg-simulation",
        "expected_generation":SIMULATION_GENERATION,
        "observed_generation":SIMULATION_GENERATION,
        "evidence_ref":f"SUP/docs/DONOR_BINDINGS.md; TTG-Simulation@{SIMULATION_REVIEWED_SOURCE}; generation {SIMULATION_GENERATION}"}
    }
    # No methods are marked as hardware or data-task qualified. The
    # borrowable Soup trainers are oriented to LLM tasks (SFT/PEFT/DPO etc.)
    # and have no demonstrated Wolf-Coin tabular MLP adapter.
    method_fit={method:None for method in SOUP_REALIZE_METHODS}
    snapshot={
       "schema":"wolf.sup-frozen-capability-snapshot.v1",
       "purpose":"close missing SUP_SIM input without claiming neural route or production admission",
       "sup_generation":generation,
       "source_product":"Wolf-Coin",
       "source_generation":package.get("source_generation"),
       "evidence_generation":package.get("evidence_generation"),
       "owner_pins":owner_evidence,
       "simulation_architecture_generation":SIMULATION_GENERATION,
       "soup_donor":{"pinned_fork_sha":SOUP_REF,
            "github_repo":soup_remote,
            "remote_commit_verified":remote_sha==SOUP_REF,
            "execution_enabled":False,
            "authority_transfer":False,
            "tabular_1x2_training_adapter_proven":False},
       "resources":{"source_sha256":sha256(resource_report.read_bytes()).hexdigest(),
            "sup_bit_readonly_fit_for_declared_small_cpu_job":True,
            "method_fit_for_soup_trainers":method_fit,
            "unverified_cpu_quota":resources.get("snapshot",{}).get("cpu_quota_cores") is None,
            "cpu_memory_observation_not_approval":True},
       "gates":{"machine_source_receipt_bound":True,
                "externally_signed_acceptance":False,
                "neural_training_authority":False,
                "soup_method_compatible_with_tabular_data":False,
                "automatic_financial_authority":False},
       "frozen_pin_currentness_only":True,
       "latest_repository_heads_not_claimed_current":True,
       "snapshot_advisory_only":True,
    }

    sim={
       "subject":"SUP",
       "sup_generation":generation,
       **binding,
       "challenge_obligations":[
         {"id":"wolf-cc0-no-postmatch-leakage","required":True},
         {"id":"wolf-restricted-odds-not-neural-training","required":True},
         {"id":"wolf-holdout-uncertain-no-profit-promotion","required":True},
         {"id":"wolf-stale-generation-fail-closed","required":True}
       ],
       "learning_package":deepcopy(package),
       "resources":{"method_fit":method_fit,
           "research_task":"tabular 1X2 result classification; no claimed Soup transformer fit",
           "sup_bit_resource_only":True},
       "donor_binding":{"donor":"soup","ref":SOUP_REF,
           "authority_transfer":False,"execution_enabled":False,
           "supported_methods":list(SOUP_REALIZE_METHODS)},
       "scoped_nogoods":[{
           "id":"wolf-cc0-v1-no-proven-soup-tabular-adapter",
           "scope":package.get("evidence_generation"),
           "blocked_methods":list(SOUP_REALIZE_METHODS),
           "reason":"no supported Soup training method is qualified for this numeric tabular 1X2 project",
           "effect_authority":False
       }]
    }
    result=deepcopy(request)
    result["sim_request"]=sim
    return snapshot,result


def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="wolf-sup-snapshot")
    for a in ("request","sup-root","cookpit","formula","srg","simulation",
              "resource-report","output-dir"):
        p.add_argument("--"+a,required=True,type=Path)
    args=p.parse_args(argv)
    snapshot,request=build(
       json.loads(args.request.read_text()),sup_root=args.sup_root,cookpit=args.cookpit,
       formula=args.formula,srg=args.srg,simulation=args.simulation,
       resource_report=args.resource_report)
    from sup_control.director import build_director_plan
    from sup_control.sim import simulate_neural_routes
    from sup_control.common import SUPContractError
    sim=simulate_neural_routes(request["sim_request"])
    plan=build_director_plan(request)
    if (plan["stage"]!="NO_VIABLE_NEURAL_ROUTE" or
        plan["artifacts"]["sup_sim"]!=sim or
        sim["reduction"]["survivors"] or
        plan["training_executed"] is not False or
        plan["authority_granted"] is not False):
        raise SnapshotRefused("source snapshot did not produce correctly gated SUP disposition")
    # prove fail-closed adversarial controls with the native SUP code
    negative={}
    for name,mutation in (
       ("stale_cookpit",("sim_request","cookpit_binding","observed_generation","not-an-authoritative-generation")),
       ("soup_authority",("sim_request","donor_binding","execution_enabled",True)),
       ("different_learning_package",("sim_request","learning_package","package_id","another-product")),
    ):
        adversarial=deepcopy(request)
        node=adversarial
        for path in mutation[:-2]:
            node=node[path]
        node[mutation[-2]]=mutation[-1]
        try:
            build_director_plan(adversarial)
        except SUPContractError as exc:
            negative[name]={"refused":True,"reason":str(exc)}
        else:
            raise SnapshotRefused(f"SUP allowed negative control: {name}")
    receipt={
       "schema":"wolf.sup-snapshot-completion.v1",
       "capability_snapshot_inputs_complete":True,
       "sup_director_stage":plan["stage"],
       "sim_result_digest":sim["result_digest"],
       "director_digest":plan["director_digest"],
       "sim_candidates_rejected":len(sim["reduction"]["rejected"]),
       "sim_candidates_surviving":0,
       "route_unavailable_for_verified_soup_methods":True,
       "snapshot_is_signed_owner_acceptance":False,
       "frozen_binding_not_latest_head":True,
       "execution_and_deployment_authority":False,
       "financial_edge_proven":False,
       "negative_controls":negative,
       "next_owner":"Full Formula / Wolf-Coin independent authority",
       "next_gate":"new typed tabular training adapter and independently qualified future data; no automatic training or betting"
    }
    out=args.output_dir.expanduser().resolve()
    if out.exists():
        raise SnapshotRefused("snapshot completion directory already exists, refusing overwrite")
    out.mkdir(parents=True,mode=0o700)
    for name,data in (("owner-capability-snapshot.json",snapshot),
                      ("sup-director-snapshot-request.json",request),
                      ("sup-sim-result.json",sim),("sup-director-result.json",plan),
                      ("capability-gate-receipt.json",receipt)):
        file=out/name
        with file.open("x",encoding="utf-8") as f:
            json.dump(data,f,sort_keys=True,indent=2)
            f.write("\n")
        file.chmod(0o600)
    print(json.dumps({"status":"CAPABILITY_SNAPSHOT_COMPLETED",
        "director_stage":plan["stage"],
        "routes_qualified":0,
        "native_negative_controls_passed":len(negative),
        "output":str(out),
        "neural_training_executed":False,
        "financial_authority":False},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
