# Wolf-Coin — guarded execution foundation candidate

**Status:** **PAPER-ONLY IMPLEMENTATION CANDIDATE / NOT LIVE-ADMITTED**
**Date:** 2026-11-23
**Source predecessor:** `54ed8dcaef3eb434bc294eb4314e98a6e384689f` on draft PR #10.
**Framework:** existing P0–P12 and additive WX-0–WX-10; no milestone self-certification.

## Implemented source surfaces

- `wolf_execution.guard`: typed paper-only intent, provider and market evidence, conservative per-account risk preflight with default trade 0.25% equity, concurrent 0.75%, daily 1%, weekly 2.5%, drawdown 5%, two-position ceiling, min order/risk and stale-data refusal. Decimal-bound money, account/currency and session identity. Caller-supplied data are **simulation inputs**, not verified broker facts.
- `wolf_execution.journal`: durable SQLite append-before-effect state machine (PROPOSED → UNKNOWN → ACCEPTED/REJECTED), strict event replay, unique starting-event CAS, refusal of duplicate execution, account/domain isolation, authoritative readback requirement and blocked new exposure while any paper effect is unresolved or open. Only the built-in `PaperVenue` can be invoked; it has no network or real order function.
- `wolf_execution.readiness`: informative, strictly read-only inventory of the real Tenfold campaign and missing requirements. It reports `real_money_permitted=false` regardless of locally asserted gate status. It does not accept an argument to enable live activity.
- `wolf_markets.mt5_probe`: dependency-injected read-only inspection seam for an explicitly matched **MT5 demo** account. Verifies login/server/currency, terminal connectivity, demo account type, orders, and positions. Uses only initialize/terminal_info/account_info/orders_get/positions_get/shutdown. Calls neither `order_send` nor `order_check` nor login, and never contains credentials.
- `wolf_core.ledger`: backwards-compatible, optional `must_be_new` atomic append control. Default existing paper event idempotency is unchanged. Strict uniqueness is required for effect transitions.

## Proof completed on KRATOS

- 92 unit/negative-control tests, including actual Linux process termination during a simulated post-journal/pre-response window.
- Missing acknowledgement before/after effect, UNKNOWN across restart, mismatched receipt, duplicate effect identity, another account/domain, capital ceilings, frozen account, session expiry, provider permission, stale data, fake live intent, and wrong MT5 account/real trade mode all produce refusal or durable UNKNOWN.
- Intent simulation is not broker-equivalent, and mock MT5 response tests are not real terminal or broker qualifications.
- No executable live connector, network effect path, MT5 demo installation, strategy with proven predictive advantage, real sportsbook interface, or owner-approved release is present.

## Authority and remaining blockers

P12 requires clean-release/replay proof, independent risk/execution review, MT5/broker account access, DEMO order + reconciliation with broker truth, stops and emergency drill, realistic sustained paper/shadow runs, fees/FX/slippage calibration, independently approved strategy, and explicit owner-signed final policy. Sports WX-10 separately requires a lawful/contractually permitted provider interface and verified settlement/readback.

No exact sportsbook or trading broker was selected, and no credentials or read-only/demo connections have been provided. K100 each is the contemplated **funding ceiling**, not a positive-return assumption. On K100, a 0.25% trade-risk policy allows at most K0.25 loss per trade before costs; provider minimums may make that infeasible, in which case the correct action is ABSTAIN, not increase risk.

Run `wolf-readiness --domain sports|trading --tenfold-db /home/kratos/projects/Tenfold/.workspace/wolf-coin-20261123/tenfold-authority.db` to inspect missing proof. This command cannot arm transactions.

## Official MT5 API references

- https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5ordersget_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5positionsget_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py

Do not interpret this candidate or a favorable SIM structural score as a claim that live money can be used. The existing KRATOS `wolf-coin-paper-preview.service` remains a read-only, loopback-only separate installed release until an independent promotion decision.

## Independent candidate readback and packaging

- KRATOS test command: `python3 -m pytest -q` => **92 passed**, including real Linux process kill during an in-flight *simulated* effect.
- Isolated offline package built with `python3 -m pip wheel . --no-deps --no-index --no-build-isolation`; SHA-256 `ad1d26049789e949d1f55f294c25498a1038fcbc73a16d729a2f2184b23f08ba`.
- Candidate packaged in `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/guarded-execution-20261123/venv`, separate from the running first-light preview. The `wolf-readiness` entry point was run from the installed wheel, reporting sports **0/24** and trading **0/13** live admission gates proven.
- Cookpit manually invoked from its qualified runtime, project `wolf-coin-execution-foundation`: source micro **PASS** (61 focused checks, no-live proof) and host heavy **PASS** (92 full tests, exact wheel hash, unchanged paper service, POST 405). Receipts retained at `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-execution-foundation/evidence/`. No recurring schedules or GPT supervisors were created.
- This candidate is **not** installed into the active paper user service, not independently code-reviewed for production, and cannot issue real-money orders/bets.
