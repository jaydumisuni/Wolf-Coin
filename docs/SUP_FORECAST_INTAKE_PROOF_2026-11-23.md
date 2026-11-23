# Wolf-Coin / SUP + SUP-Bit forecasting intake — 2026-11-23

**Status: ACTUAL SUP Director handoff executed; source truth NOT independently qualified; no neural training or real-money admission.**

## Recovered authority and source

- Wolf-Coin candidate source at first materialization: `b9240c214b54bcccae35987306edc03b26bdd0f6`, from isolated Patrol-registered Wolf-Coin worktree.
- SUP G5 Director generation: `sha256:15d7530cfdcda94c151fb20be55eff429bae4c94c76a1da4e73b926960c19b2c`; original existing `sup director` CLI invoked on KRATOS, not recreated in Wolf-Coin.
- Source data retained privately: Football-Data.co.uk Premier League historical E0 CSV. Recorded Bet365 quoted *opening* odds **do not prove account-executable or timestamped prices**.
- Season exact SHA-256:
  - 2022/23: `8442792d3b614c94ea3cf381bd2736805889cc1713169035368fff19c3d02380`
  - 2023/24: `b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3`
  - 2024/25: `d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4`
  - 2025/26: `3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62`
- Derived corpus: **1,520 matches**; 760 training (2022/23 and 2023/24), 380 validation (2024/25), 380 **previously inspected** diagnostic (2025/26). SHA-256 of canonical derived feature content: `900a45ead9feb37b85450bda63ebcb45e386eb308f5593d66047548af59e87f6`.
- Features include only fixed-shrinkage previous-date team form, scoring, conceding, relative experience and bookmaker no-vig probabilities. Same-day score changes cannot change features for another fixture that day. Full-time score/result consistency, hashed source, non-overlap, odds bounds and missing-data controls are tested.

## Direct CPU predictive-quality result

- Baseline: no-vig bookmaker opening odds.
- Model: fixed, small, L2-regularized market-offset softmax on the prior-day features, trained on 760 fixtures using CPU NumPy. Exactly three predeclared regularizers: 0.02, 0.10, 0.50.
- Validation bookmaker baseline Brier `0.578663803`, log-loss `0.970757673`.
- Best CPU candidate (penalty 0.50) Brier `0.580325109`, log-loss `0.973309196`. **Candidate is worse on both measures**; Brier gain = `-0.001661306`.
- Full candidate score table is stored in the private research report. Candidate status `ABSTAIN_NO_VALIDATED_FORECAST_EDGE`, `selected=false`, `profit_proven=false`, `live_ready=false`.
- Already-examined 2025/26 diagnostic has baseline Brier `0.611512208` and log-loss `1.018547434`; it is **not** an untouched final test. There was no hypothetical bet selection by this CPU model.
- Actual complete source job on KRATOS: ≈0.39 s wall time, peak resident memory **41,148 KiB**. These are a single-host measurement, not a resource-scaling benchmark.

## Real SUP handoff

- Request and corpus are sealed privately under Wolf-Coin `.workspace/research/sup-sup-bit-forecast-20261123/b9240c214b54bcccae35987306edc03b26bdd0f6`.
- The package contains exact source and feature SHA-256, product scope, explicit negative evidence, counter-worlds, forbidden regressions, and `source_truth_qualified=false` plus `neural_realization_allowed=false`.
- Actual `sup director` output: **`AWAIT_SOURCE_QUALIFICATION`**, reason `source truth is not qualified`; digest `sha256:a4d1030ecfacab7423abfbb427fc98892a3bc1ee3abba426a0edfaf429b7afef`. It executed no training and granted no authority.
- SUP source qualification requires an independently reviewed feature and quote-timing/rights record with exact source generation, not just a locally set boolean. No fabricated external receipt.

## Actual SUP-Bit contribution

- KRATOS private SUP-Bit v14 `runtime/resources.py` was invoked **read-only** for a bounded memory estimate, without copying proprietary source into public Wolf-Coin or importing its PyTorch trainer.
- Declared small research workload fit the observed host envelope (`FIT`, estimator only; observed effective available RAM ≈5.92 GB, 16 logical CPUs); unknown CPU quota remains unverified.
- The current full SUP-Bit import requires PyTorch in its qualified environment; Wolf-Coin system Python lacks it. The existing language-model-oriented SUP-Bit implementation has not been qualified as a 1X2 football classifier and was **not** represented as having trained one.
- No M0–M9 SUP-Bit milestone, SUP training execution lease or neural model quality acceptance was conferred.

## Product state and next independent frontier

The candidate is ready for source-qualification **review**, not neural realization or real-money funding. Qualification needs:
1. Independently verify source/timestamp semantics, data provenance and permitted ML/automation rights.
2. Bind approved train/validation evidence to the exact Wolf-Coin source and a fresh SUP/Tenfold authority packet.
3. Use a materially unexamined chronological dataset for model-quality evaluation; 2024/25 and 2025/26 have already been examined.
4. Demonstrate predictive improvement against bookmaker prices, uncertainty and realistic fill/cost bounds; abstain if not.
5. Evaluate a genuinely supported tabular/temporal neural method, *then* benchmark optional SUP-Bit compression and CPU footprint. No release based solely on training loss.

**No financial effects, network betting automation, account credentials or real funds used.** The running paper console remains a separate safe runtime.


## Native KRATOS release and manual Cookpit review

- Final source commit for UI and package: `7b56d694cade3ee70524a00a495a570d0b3f8faf`.
- Frozen standalone Python wheel `wolf_coin_core-0.1.0a3-py3-none-any.whl` SHA-256 `6e368eaf913de6846d0f1e189bf6835476661c78e71bf2e01bbbdfd188dc08d5`. Offline build and install passed.
- Core user-service release installed in `/home/kratos/.local/share/wolf-coin-paper/releases/7b56d694cade3ee70524a00a495a570d0b3f8faf/venv`; no NumPy dependency added to the core paper resident. The optional `research` extra is separate from the read-only service.
- Packaged `wolf-lab-cpu` executed in a separate research-only venv using already installed host NumPy, and produced **exactly matching** JSON feature corpus, score report and SUP Director request compared with the frozen source run.
- Source-bound SUP Director result remains `AWAIT_SOURCE_QUALIFICATION`, not a trained neural model. The independent unqualified-data check is maintained.
- Read-only UI now includes `http://127.0.0.1:18766/forecast`, visible in Brave on the KRATOS desktop. Sports, Trading, Strategy Lab, Forecast CPU, Funding and Health all return HTTP 200. POST is denied with HTTP 405; health advertises `PAPER`, `live_enabled=false`, `remote_enabled=false`; service listens only on `127.0.0.1:18766`.
- Service startup remains pinned to exact source commit. Existing virtual ledger was not reset. Previous release and service definition were retained for rollback under `.workspace/proof-history/sup-cpu-replay-20261123/previous-paper-service.unit`.
- Cookpit manual **micro PASS**: 14 focused tests, exact source/input hashes, SUP real stage, negative predictive advantage; receipt `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-sup-forecast-cpu/evidence/20261123T123356Z-micro-fd39602851c6.json`.
- Cookpit manual **heavy PASS**: 227/227 full tests, exact wheel hash, installed release, HTTP and no-live controls, SUP-Bit read-only resource proof; receipt `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-sup-forecast-cpu/evidence/20261123T123358Z-heavy-fd39602851c6.json`.
- These are product source/runtime acceptance checks, **not** independent data licensing qualification, profitable-edge evidence, SUP training approval, SUP-Bit production admission or real-money release.

**Next frontier:** independent source/timestamp/use-rights review before SUP neural realization, followed by genuinely supported temporal/tabular model, qualified CPU training lease, and a new untouched future period. Do not use 2025/26 as unseen data or initiate bets until those conditions and independent real-money risk/provider gates are fulfilled.
