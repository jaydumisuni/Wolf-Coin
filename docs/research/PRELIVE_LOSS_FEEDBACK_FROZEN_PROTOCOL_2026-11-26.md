# Wolf-Coin: loss-feedback and predictive superiority — pre-live frozen protocol

**Frozen before running the historical multi-season comparison, 2026-11-26.**

## Existing evidence and source boundaries

The already-qualified CC0 frozen 8-unit MLP reproduced the training
weights, but its independent 45-match 2026/27 holdout does not establish
statistical superiority. An earlier bookmaker Elo experiment lost K21.39
virtually and the subsequent validation abstained. Those results are
unchanged. The private Football-Data historical odds archive is
comparison-only, *not a neural training source*.

This is a NEW offline replay generation and is NOT the old frozen model
nor a production release. It uses the existing Wolf-Coin/CC0 feature
pipeline and its pinned CC0 upstream source and SHA-256 input mapping.
No financial-platform access, private credentials, API calls, installed
Wolf service changes, or transactions are part of this protocol.

## Fixed, before evaluation

- Train exactly once on CC0 2017/18–2020/21 (1,520 outcomes).
- Model: existing deterministic NumPy 10→8→3 MLP, seed 17,
  350 updates, learning rate 0.07, L2 0.015. No hyperparameter search.
- Independent historical *exploratory* four-fold research windows:
  2021/22, 2022/23, 2023/24, 2024/25, 380 results each.
  All these seasons are already-known historical data, not an untouched
  future holdout. Reset the calibrator for each evaluation season.
- Day-scope causality: make all forecasts using features from earlier match
  days and a pre-settled learner version; commit their event IDs,
  timestamps and probabilities before admitting ANY result from the same
  calendar day. All same-day settlements follow the full forecast batch.
- Learning mechanism: a bounded 3-class logit-bias calibrator with
  online cross-entropy gradient step 0.04, regularizer 0.001, bias cap
  +/- 0.70. Update after a source-matched settlement receipt whether it
  is a win or loss, with a new immutable version and replayable journal.
- All paper receipts use identical *synthetic* odds 2.0 and stake 1.0
  for deterministic test ledger accounting; neither these odds nor the
  simulated P/L are claimed market-executable or fed to the model.
- Scoring: proper multiclass Brier and log-loss of final committed forecasts;
  comparator A = frozen MLP; B = historical CC0 training class prior.
  Comparator C = bookmaker de-vigged opening quote for 2022/23,
  2023/24 and 2024/25. Bookmaker quote CSV is private and used
  exclusively for matching and **scoring**, with exact source hashes
  and 380-of-380 match/source reconciliation required.
- Bootstrap: calendar-match-day cluster resampling, exactly 2,000 draws,
  deterministic seed 20261126 (frozen); independent market comparison
  seed +1. 95% percentile CI.
- Predeclared historical predictive consistency gate: adaptive Brier
  improvement >= 0.005 **AND** log-loss improvement >= 0.005 in EACH
  of the 3 market-comparable seasons; paired clustered market-minus-
  adaptive Brier interval's lower bound strictly >0. Also require
  improvements of >=0.005 Brier and >=0.005 log-loss versus frozen MLP
  in EACH of all 4 seasons and a positive lower bootstrap bound.
- A failed gate is a genuine negative result; never tune it away,
  reframe no bets as earnings, or promote funding. Even a positive
  exploratory gate does NOT prove future superiority without a new
  independently frozen source and genuinely fresh future observations.
- Persist individual immutable private season journals, a sealed report,
  source SHA-256 and negative-control outcomes. Reports disclose the
  previously inspected data windows. Source and protocols only in
  public Git; all raw CC0 and quote data, private journals remain
  on KRATOS under .workspace/research.

## Exit criteria

1. **Learning mechanism pass** requires source-bound precommitted forecasts,
   exact unique and settled receipts, both losses/wins updating a bounded
   calibrator, no same-day leakage, identical resume/restart state,
   rejection of tamper, replay, nonfinite inputs and chronology violations.
2. **Predictive superiority** is NOT marked proven unless the fixed
   historical consistency gate passes AND a future, genuinely untouched,
   source-bound, independent out-of-sample holdout is later scored.
3. **Real-account learning** remains separate: provider authenticated
   outcome readback, settlement identity, currency, exact fees, manual
   authority, real reconciliation and programmatic link to the application
   backend need real-provider proof. A synthetic receipt cannot prove it.
4. **Financial profit** requires independently verified, net-of-cost
   outcomes and cannot be inferred from Brier or synthetic stake returns.
5. No real-money execution or provider action is introduced here.

Result is classified correctly as a **completed offline qualification with
PASS/FAIL verdict**, not an assertion that all desired quantitative gates
are satisfied.
