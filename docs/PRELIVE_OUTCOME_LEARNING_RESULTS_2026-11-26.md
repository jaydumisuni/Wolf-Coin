# Wolf-Coin pre-live learning and prediction review — 2026-11-26

## Scope and repository authority

Target: self-contained Wolf research laboratory (wolf_lab), **no live account**,
no provider session, no funds, no funded order and no model promotion.
Implemented independently in branch
work/wolf-prelive-outcome-feedback-20261126 based on research HEAD d9cfb04.
Frozen protocol commit 6618fc0 **precedes** the new research diagnostic.
Implementation commit 026d7e9. Existing trained artifacts, other branches,
native installed Wolf-Coin, paper service and private training data remain
unchanged. All processing was local/offline using pinned existing sources.

## A. Learning after loss — functional qualification

- Forecast input is a distinct offer type without a result/outcome field.
- Freeze each match day's predictions and at most one hypothetical daily
  selection **before** accepting independent (simulated historical) outcome
  receipts. Require next-day evidence and exact match identities and
  pinned source SHA. Refuse premature, duplicated, missing, changed or
  cross-period settlement.
- Train the adaptive **Elo football research model** after that day's
  entire settled result batch; retain a separate unupdated control. A
  test verifies that a losing paper decision and incorrect forecast lead
  to changed subsequent probabilities, whereas the control stays frozen.
  Learning is from *all settled match results*, not solely losing bets.
- The hashed two-stage daily journal was independently checked against
  Brier calculations, virtual wager outcomes, model-state sequence,
  bankroll, drawdown, account-free paper constraints and report totals.
  Tampering tests reject altered journals and inconsistent summary values.

**Verdict:** historical offline outcome-driven feedback and strict
prediction→settlement mechanics **PASS**. This verifies this Elo adapter;
it does **not** yet establish that a future real provider settlement is
independent/authenticated or that the separate frozen neural MLP is
automatically retrained through a live account. The application bridge's
observation transaction status PENDING→SETTLED still has no trustworthy
1X2 result/price/paid-out record that qualifies as a verified learning
receipt. A real provider outcome adapter will be required later.

## B. Consistent advantage over bookmaker market — falsification

Private Football-Data EPL E0 research opening-quote files, each 380 matches:
- E0-2223.csv SHA 8442792d3b614c94ea3cf381bd2736805889cc1713169035368fff19c3d02380
- E0-2324.csv SHA b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3
- E0-2425.csv SHA d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4
- E0-2526.csv SHA 3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62

Anchored retrospective folds (lower three-way Brier is better):

| Fold scored | Adaptive Elo Brier | Frozen control Brier | De-vig market Brier | Hypothetical net, initial K100 | Paper bets / losses |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023/24 | 0.577161 | 0.602845 | 0.533123 | -K18.414962 | 100 / 83 |
| 2024/25 | 0.596184 | 0.613564 | 0.578664 | -K10.711534 | 92 / 71 |
| 2025/26 | 0.616015 | 0.623532 | 0.611512 | +K16.994412 | 105 / 65 |

- 1,140 total predictions from 3 previously inspected years.
- 343 post-settlement update days; 296 update days with a losing paper
  selection or an incorrect most-likely forecast; 297 paper decisions,
  219 hypothetical paper losses and 78 paper wins. No real wagers.
- The **adaptive** model improves on the separately frozen Elo control in
  each fold, showing useful outcome assimilation. But it is **worse than
  the market benchmark in every fold**.
- Frozen predeclared 2,000-replicate day-cluster bootstrap 95% interval
  for *market Brier minus adaptive Brier*:
  **[-0.0303551392, -0.0140047689]** — entirely negative.
- Real-world bet quotes and provider fills are not independently verified.
  One superficially profitable retrospective fold is not evidence of
  predictive superiority or positive expected financial returns.

**Verdict:** retrospective qualification **FAIL: no consistent market edge**.
The previously recorded -K21.390526 virtual Elo experiment, and the
2025/26 frozen strategy that correctly abstained from all betting,
are still valid and have not been edited. Those were separate strategy
generations; this diagnostic does not replace them.

## C. Account-free future holdout infrastructure

Using the existing byte-pinned CC0 2026/27 fixture snapshot and previously
frozen historical CC0 MLP model, Wolf separately sealed 270 *unscored*
matches with scheduled dates 2026-11-28 through 2027-05-30.
The prospective freeze contains only fixture identity, prior-only
features and precomputed class probabilities — **no future results**.
No bookmaker quotes or economic edge can be inferred at freeze time.
The schedule is provisional and source-stale; any rescheduling will
require separately audited identity reconciliation, never rewriting
the sealed forecast.

- Freeze cutoff: 2026-11-26.
- Original frozen MLP file SHA 2eb587952d5fb72dd25fcaa50aac9b46d6c4e6d3be33a02b502bb7e5a09a3fba.
- Original CC0 2026/27 source SHA bb91f0ab3e8359df163bb9ec98549bfed85e200dd4c32f3bd606b5890d932dd2.
- Forward predictions SHA 53944d9ed2869dd0114a29859df1196c525c7229f4cdac8d3c55f5b92819bec9.
- Forward digest SHA decefdda4ceb1d345d620e9f88a2007498e8d40e0b076ca04dac20df3e942a88.

The independent scoring function will reject unknown IDs, duplicate
results, early settlements and claims about already-played fixtures. It
will score later results against the frozen probabilities, but **does not**
call that a market edge without usable pre-match market quotes.

## D. Tests, artifact locations, and release boundary

- Source tests: **450/450 PASS** with 13 focused pre-live tests, including
  deliberate rejection and later-forecast-change tests.
- New pre-live data/journal output in existing owner-private proof-history
  (mode 0700 folder; mode 0600 results):
  - .workspace/proof-history/prelive-outcome-feedback-20261126/verified-v2/prelive-feedback.json
    SHA b64a496b77a5b6f52f89c62b5c68e7d89dc3bd1ba86bd517a4fdb4aaf2f5c983
  - .workspace/proof-history/prelive-outcome-feedback-20261126/verified-v2/prelive-feedback-journal.json
    SHA 93801892a54240111e66820f211b46e29cf3071d18f242d40dc1e43851cd5ac9
  - .workspace/proof-history/prelive-outcome-feedback-20261126/forward-freeze/forward-freeze-20261126.json
    SHA 53944d9ed2869dd0114a29859df1196c525c7229f4cdac8d3c55f5b92819bec9
- Source has two offline, fail-closed entrypoints:
  wolf-prelive-feedback and wolf-prelive-forward.
- No native Wolf-Coin installation or financial state was changed; no
  model retraining was admitted into production, and no raw private
  bookmaker CSV or scored future dataset was committed to Git.
- The original source worktrees, frozen models, existing backend and
  independently running supervisors and other projects were untouched.

## Gate results before connecting a real account

- **Historical loss-feedback mechanics:** PASS; Elo offline, signed/hash-linked
  journal integrity checked, retrospective simulated outcomes only.
- **Prospective no-account forecast freeze:** CREATED, pending future events.
- **Robust repeated predictive superiority vs market:** NOT PROVEN; new
  retrospective diagnostic explicitly failed the frozen threshold.
- **Real-provider settled-loss feedback:** NOT VERIFIED; source/provider
  reconciliation not available without true account receipts.
- **Automated financial execution:** OFF, not authorized.

Next useful work without a real account: observe *new, previously unseen*
public match results as they occur; recover independently time-stamped,
legally usable opening odds; reconcile rescheduled fixtures; score the
frozen probabilities across a meaningful future window; propose genuinely
new models only on separately designated training/validation data and
freeze them before the next untouched holdout. Do not select parameters
from these already examined folds and present that as new proof.

**Already documented — Update existing documentation.** This evidence
extends Wolf's earlier HISTORICAL_REPLAY_PROOF and CC0_NEURAL_POSTFREEZE_PROOF;
it does not replace their independent source/authority boundaries.
