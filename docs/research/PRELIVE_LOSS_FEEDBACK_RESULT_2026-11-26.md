# Wolf-Coin pre-live loss learning and predictive-superiority qualification

**Status: offline mechanism PASS; predictive-superiority FAIL; no model promotion.**
**Date: 2026-11-26.**

## Recovered baseline

Wolf-Coin's frozen CC0 10→8→3 neural training, typed tabular weight
reproduction, market benchmarking and historical research documents
already existed. This work does not overwrite those records or reclassify
the earlier **K21.39 virtual Elo loss** as a win.

The protocol was frozen in Git **before** loading these seasons for this
specific candidate:

- Protocol/source freeze: `74485155dddcdac0027d1c64c77aea8cb09f721e`.
- Corrective verifier commit: `8554083be1d32148a1493320911910d0d242962e`.
- Exact post-correction replay: private results and **all four journals were
  byte-for-byte identical** to the source-frozen run.
- Historical data: CC0 outcomes are the only training and online-learning
  input; the private Football-Data bookmaker CSVs are for score comparison
  only, not training and not redistribution.
- The windows below are historical and already inspected; these are
  reproducible retrospective diagnostics, NOT a new untouched future
  holdout.

## Offline settlement-to-learning result

- Training: 1,520 CC0 football outcomes, 2017/18 through 2020/21.
- Evaluation: 1,520 chronological forecasts, 2021/22 through 2024/25.
- Each fixture had a unique forecast ID, model-version field and
  precommitted probabilities before the settlement stage.
- Each day was forecast as a full batch before any same-day result
  updated the calibrator.
- All 1,520 simulated receipts were settled, 736 were losing selections
  and 784 were winning selections using deliberately **invented fixed
  2.0 decimal odds and a nominal stake of 1**. These values do not
  represent executable odds, revenue or an actual account ledger.
- Losses and wins caused bounded deterministic learner updates, with
  version advancement, source/forecast identity matching, duplicate
  detection, wrong-source refusal and chronological checks.
- A new process can reconstruct the exact updated parameters from the
  sealed private journal. A standard-library verifier separately
  recomputed proper scores and receipt counts from the immutable
  precommitted forecasts.
- Separate constructed distribution-shift unit test proves that the
  feedback mechanism **can** improve subsequent predictions in an
  artificial scenario. It does not establish market superiority.

**Mechanism disposition: PASS in offline simulated settlement replay.**
It is not yet an authenticated, actual real-account settlement adapter.

## Frozen historical proper scores

Lower multiclass Brier/log-loss is better.

| Historical season | Adaptive Brier | Frozen MLP Brier | Market de-vig Brier |
|---|---:|---:|---:|
| 2021/22 | 0.572942683 | 0.568621700 | no quote comparison |
| 2022/23 | 0.604346961 | 0.602278846 | 0.573498527 |
| 2023/24 | 0.560741879 | 0.555472642 | 0.533123373 |
| 2024/25 | 0.631696849 | 0.629035342 | 0.578663803 |

The comparison reconciled 1,140 of 1,140 fixture identities and source
results for the three quoted seasons. It uses their exact pinned file
hashes and is independent of the calibrator's inputs.

Predeclared 2,000-sample match-day-clustered bootstrap:

- Pooled frozen-minus-adaptive Brier gain: **-0.003579961**,
  95% interval **[-0.007161808, -0.000191599]**.
- Pooled bookmaker-minus-adaptive Brier gain: **-0.037166662**,
  95% interval **[-0.047768400, -0.026422853]**.
- Both intervals are entirely **below zero**, meaning the adaptive
  candidate is less accurate, not more accurate, under this protocol.
- The fixed historical superiority requirements fail on each quoted
  season and against the frozen model. No re-selection, parameter
  tuning, newer score refitting or performance cherry-picking was
  performed after obtaining these results.

**Predictive superiority disposition: FAIL for this candidate.**
This is not a profitable strategy or evidence to place real orders.

## Independent machine verification and exact replay

The lightweight, no-NumPy, no-provider, standard-library audit command:

`python3 -m wolf_lab.prelive_verify --evidence-dir PRIVATE_DIRECTORY`

replayed all four journals, verified their SHA-256 artifact manifests,
seal digests, event identity/order, 1,520 actual feedback events, 736
losses, exact adaptive Brier and log-loss figures, and no fake financial
authority fields. Altered receipt bytes, a forged score with a newly
computed outer seal, replayed or wrong-source receipts are rejected by
negative tests.

- Source suite: **450 passed**.
- Source-frozen private report SHA-256:
  `c56de3dc56fff678130f677fa117942cc0ccbb03c5d741dc8bd48589c5ee0799`.
- 2026-11-26 second evaluation after journal-canonicalization correction:
  identical report and **identical four journal files**, checked by `cmp`.
- Source-private evidence originals:
  `/home/kratos/projects/Wolf-Coin/.workspace/research/prelive-loss-feedback-20261126-frozen-7448515/`.
- Reproducibility proof:
  `/home/kratos/projects/Wolf-Coin/.workspace/research/prelive-loss-feedback-20261126-replay-8554083/`.
- These are SHA-256 integrity and deterministic machine checks;
  they do **not** constitute independent human signatures or proof
  of real provider settlement authenticity.

## Explicit model promotion and real-account boundary

**Do not promote the adaptive challenger.** The independently
recomputed disposition is `REJECT_KEEP_FROZEN`. Existing Wolf-Coin
installed model weights, resident application, account states, schedules,
paper ledger, execution authority and live market access have **not**
been modified by this work.

The next predictive strategy requires genuinely different pre-match
features, a *new* source/protocol freeze and a future independent holdout,
because repeatedly selecting candidates against these same exposed
2021/22–2024/25 seasons would be data snooping. Historical results
can measure robustness but cannot be relabeled unseen.

Connecting real-account outcomes later additionally requires truthful
provider-specific transaction/settlement receipt identities, actual
accepted price, currency, fees, final settled state and duplicate-safe
readback. The offline feedback journal can consume validated outcomes;
it currently does **not** auto-consume such live account receipts.

**Contribution classification: New research mechanism + correction +
verification + update of existing Wolf-Coin documentation.**
No new installer, no installed backend change and no financial action.
