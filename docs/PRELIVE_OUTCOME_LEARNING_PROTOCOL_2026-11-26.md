# Wolf-Coin pre-live outcome-learning qualification — frozen research protocol

**Frozen before executing the new diagnostic:** 2026-11-26.
**Code scope:** standalone Wolf laboratory offline research; no production model promotion, payment, provider session, funded orders or deployment authority.
**Frozen existing evidence:** 2023/24→2024/25 historical Elo paper result -K21.390526; predeclared 2023/24 train + 2024/25 validation → 2025/26 final admitted no candidate, 0 bets. Neither result is erased or restated as an edge.

## A. Two different claims

1. **Settled-outcome learning correctness:** present only pre-outcome features and historical quoted odds to the candidate; seal each day's predictions and a hypothetical bounded paper decision before admitting an outcome receipt. Verify independently supplied (simulated historical) settlements match exact pending identities and arrive later; learn only after all outcomes for a date settle. Demonstrate losing **predictions** and losing **paper decisions** are retained, scored and cause attributable model state changes. Reject duplicated, premature, inconsistent, missing and forged settlement receipts, including replay after an event has already been settled. Preserve a deterministic hash-linked ledger; seed a separate no-update control model.
2. **Consistent predictive superiority:** compare the after-settlement-update model against de-vigged historical market probabilities, a separately frozen no-update Elo control, and the quoted prices for hypothetical paper decisions. Evaluate chronologically over three *retrospective* seasonal folds (train 2022/23 → 2023/24; train 2022/23–2023/24 → 2024/25; train 2022/23–2024/25 → 2025/26). Never choose model weight, threshold, training schedule, or strategy based on these fold outcomes. They are already examined historical years and **not new untouched holdouts**.

## B. Inputs, boundaries and predeclared rule

- Private pinned Football-Data.co.uk E0 CSV snapshots:
  2022/23 SHA-256 8442792d3b614c94ea3cf381bd2736805889cc1713169035368fff19c3d02380;
  2023/24 SHA-256 b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3;
  2024/25 SHA-256 d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4;
  2025/26 SHA-256 3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62.
  Historical odds are **not authenticated executable quotes**, and results in a CSV do not constitute a third-party provider settlement receipt.
- For every match day, first produce forecast/market probabilities and eligible paper picks using **only** fixture identities, calendar days, trained ratings and opening odds. The entire day's outcome map is provided only to a separate settle_day operation after predictions are sealed. Each paper receipt is labeled synthetic/historical, never a funded position.
- Historical Elo hyperparameters and guardrails stay identical to the frozen ReplayPolicy. At most one daily hypothetical selection, odds ≤5, expected EV >0.05, stake ≤0.5% of virtual bankroll, 2% hypothetical winning-profit commission, K100 initial virtual bankroll.
- Candidate gets an incremental Elo update **after all matches on the date settle**, including incorrect forecasts and losing decisions. The no-update control keeps frozen train-period ratings. A forecast error is **not equivalent** to a negative financial return; track both separately. Update from **all final outcomes**, not only losing bets, to avoid outcome-selection bias.
- Pooled 95% day-cluster bootstrap (fixed seed 20261126; 2,000 replicates) of market Brier minus adaptive Brier. Days are clustered within their historical fold.
- **Retrospective diagnostic pass**, not financial release: each fold has at least 300 scored matches; adaptive Brier is better than de-vigged market by ≥0.005 in **every** fold; pooled bootstrap lower 95% bound >0; and hypothetical net return after modeled commission is positive in each fold with max drawdown ≤20%, at least 200 paper decisions total. No tuning on failed tests.
- **Genuine superiority gate:** retrospective diagnostic alone never suffices. It also requires a separately time-frozen, future **unexamined** outcome period, contemporary independently usable prices and independent validation before declaring repeatable edge. Until those exist, the gate must be NOT_PROVEN regardless of retrospective numbers.
- **Live execution gate:** always false. This qualification cannot approve real money.

## C. Evidence handling

The new driver must write source-digest-bound JSON reports and a hash-linked per-day prediction→settlement journal in a **private** proof directory, not Git. No raw CSV, live credential, wallet data, or private D-XQT binary is to be committed. Guard against replay, day reordering, outcome injection before prediction, missing IDs, and settlement tampering via focused negative tests. Existing frozen model files, dashboards, services and production branch are unchanged.

**Decision on failure:** preserve negative results, abstain from live financial execution, and classify the next data/test requirement rather than silently loosening thresholds.
