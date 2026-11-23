# Wolf-Coin — Multi-domain WX roadmap supplement

**Status:** proposed construction contract, not admitted production authority.
**Date:** 2026-11-23.
**Original authority:** docs/MASTER_PLAN.md, docs/ROADMAP.md (P0–P12), docs/RISK_POLICY.md. Preserve those gates.
**New domain:** sports research/paper execution with independent settlement and bankroll controls. Trading remains the first original domain.

## Operating law

One local resident control plane and two **financially isolated** domain instances: trading and sports. Shared evaluation, journaling and optional cognition must never imply shared money, authorization, risk allowances or release admission.

Owner halt > per-account risk veto > verified external account/provider truth > fresh validated data > deterministic strategy > candidate probabilistic/model advice. Unknown state blocks new financial effects. Every decision may return ABSTAIN. A desired growth milestone never implies a profitable strategy or increased risk.

The KRATOS dashboard's two tabs are observational surfaces; the native daemon owns scheduling, recovery and audit. No Docker, GPU, Prime OS installation or neural inference dependency is required for the deterministic first-light milestone.

## WX-0–WX-10: explicit gates and acceptance

| Gate | Depends on | Implement | Acceptance and hostile controls |
|---|---|---|---|
| WX-0 — authority | P0 | Accepted additive ADR, exact generation, source rights, full independent release inventory | No silent change to P0–P12 or private cognition contracts; unqualified capability stays unavailable |
| WX-1 — survival | P1–P3 | KRATOS native daemon, scheduling, resource budgets, health and restart | Power/network loss, stale clocks, browser closure, CPU/memory pressure; replay accurate state |
| WX-2 — money domains | P1/P5 | Separate account/bankroll ledgers, deposit/withdrawal, FX, fees, reserve and exposures | No inter-domain leakage; conserved accounting across restarts, reversals and conversion |
| WX-3 — sports data | P4/WX-2 | Licensed fixtures/markets/odds/results; settlement including draws/voids/cash-outs | Wrong fixture ID, stale quote, contradictory source, postponed event, result/source rights |
| WX-4 — Formula/SIM lab | P6/P7/WX-3 | Optional bounded mathematical/simulation adapter; calibrated forecasts and true cost-aware EV | Held-out calibration vs market baseline; no future leakage; exact replay and parameter sensitivity |
| WX-5 — sports risk | P5/WX-2 | Stake, event exposure, accumulator correlation, loss caps, provider limits | Minimum stake larger than allowed risk blocks; duplicated/split stakes do not expand risk |
| WX-6 — COG SHADOW | P7/WX-1 | Product-scoped read-only self-model, grounded diagnostics and optional HOT/WARM/COLD routing | No read-only COG effect rights; model outage safe fallback; forged/stale evidence denied |
| WX-7 — recovery | P3/WX-2/WX-3 | Intent journal, immutable IDs, idempotency, lost-ACK reconciliation, session and frozen-account controls | Unknown bet/order never blindly retried; expired session and frozen account block exposure |
| WX-8 — paper | P9/WX-4/WX-5/WX-7 | Independent sports/trading shadow runs, drift metrics, costs and recorded incidents | Realistic out-of-sample results, exact accounting and replay; no unexplained open effect |
| WX-9 — learning | P10/WX-8 | Outcome→candidate→negative controls→independent assurance→second-use | No model self-certification, no auto strategy promotion, old-corpus non-regression |
| WX-10 — console/release | P11/P12/WX-6/WX-8 | Two local tabs, reports, halt, approvals; independent guarded-live gates per domain | Actual provider/API permission, owner-signed authority, emergency/recovery proof before live |

### Mandatory corrections from the 2026-11-23 TTG-Simulation design review

The initial WX draft covered only 35 of 40 *declared* structural hostile obligations. The corrected candidate covered 40 of 40, but that was a **documentary design comparison**, not runtime fault injection or a success percentage. Five missing contracts are now explicitly required:

1. Data-source licensing, access terms and retention limits (WX-3).
2. Funding and currency reconciliation for deposits, withdrawals, fees and conversions (WX-2/WX-7).
3. Frozen, limited or suspended sportsbook account states (WX-7).
4. KRATOS Linux to Windows MetaTrader 5 architecture, or a separately qualified direct broker API (P8/WX-1).
5. Expired session/authorization invalidation and safe ambiguous-effect reconciliation (WX-7).

### Provider and execution boundary

Account ownership alone does not establish permission to automate operator services. Unsupported or disallowed automation remains research/paper/manual-owner mode. Each operator or broker must supply a qualified execution interface and independent authorization. No website evasions, automatic funding, loss-chasing, martingale or direct unverified AI orders.

### Separate release law

Existing trading P12 readiness cannot admit sports live. Sports WX-10 needs its own regulator/operator policy, source rights, position/stake minimum check, live-pilot approval, rollback, reconciliation, accounts and historical evidence. An independent reviewer must verify real release proof, not a simulation score.

### Proposed typed seams

EvidenceSnapshot; CandidateDecision; IndependentRiskVerdict; EffectIntent; EffectReceipt; LearningCandidate. Each carries domain, source/version, timestamps, digest and scope; never duplicate existing Wolf-Coin schemas without a migration review. Formula/SIM, COG and neural providers return advisory evidence; Wolf-Coin owns actual risk, accounts and effects.

**Next safe frontier:** P0/WX-0, then source implementations with exact-head evidence. No live trading or sports funding is implied by this document.
