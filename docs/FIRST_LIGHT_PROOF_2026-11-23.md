# Wolf-Coin first-light source candidate — evidence record

**Date:** 2026-11-23
**Status:** SOURCE CANDIDATE / NOT P0, P1 OR WX GATE PROVEN
**Branch:** `work/wx-tenfold-cookpit-20261123`
**Source implementation head tested:** `60d02ca23dfe74324ebc89051ef862900d3b6140`
**Protected main at start:** `387822d6547e6d4b34010e81ab076c56cd0ebc53`
**Pull request:** #10 (draft; no merge).

## Built

- `wolf_core`: typed domain/account/UTC/Decimal contracts, SQLite WAL event chain, compare-and-swap append, replay verification and separate paper bankroll accounts.
- `wolf_sports`: immutable 1X2 football quotes, explicit draw outcome, normalization of three-way bookmaker overround and simple expected-return arithmetic.
- `wolf_guard`: paper-only risk abstention, unqualified-source refusal, stale-price refusal and a fixed aggregate 0.5% outstanding sports-paper risk ceiling even across multiple tickets.
- `wolf_core.cli doctor`: read-only SQLite integrity report; absent database returns UNINITIALIZED and is not created. All reports explicitly say `live_enabled: false`, `execution_adapters: 0`.
- `tests`: negative controls for bad contracts, concurrent writes, duplicates, replay/tampering, paper isolation, frozen and halted accounts, payout assertions, no-lookahead quote age, forecast qualification, correlated stake splitting and doctor behavior.

## Prove — exact source

- Isolated Python: **3.13.5**, command `python -m pytest -q` -> **19 passed**; command `python -m wolf_core.cli doctor --db /tmp/wolf-coin-nonexistent-first-light-20261123.db` -> `UNINITIALIZED`, no live capability.
- Remote source commit creation used a fixed expected branch HEAD and **Git blob SHA-1 checks** against the exact tested bytes, including all modified files.
- Cookpit manual readback of `60d02c...`: micro PASS, heavy PASS, eight critical source Git blobs identical.
- Cookpit evidence on KRATOS: `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-remote-candidate/evidence/20261122T233417Z-micro-9d522b2996e4.json` and `.../20261122T233420Z-heavy-9d522b2996e4.json`.
- The Tenfold Gen1 derived 24-node campaign remains at digest `61dfcc86df233db4585daa568c2e036caa16bc3a023958e4d5c886add6e77442`. This is derivation evidence, not implemented roadmapping.

## Important limitations and hostile assumptions

1. No KRATOS Wolf-Coin source checkout or installed package. Patrol project-root registration is blocked by the Oracle node's no-new-privileges restriction on its authorized privileged helper. Do not create unregistered project source outside the registered root.
2. No live-money routes, bookmaker API, MT5 execution, match feeds or neural autonomy. `source_rights_confirmed` is only a paper input assertion, not independent documentary license verification.
3. The ledger hash-chain is not anchored externally and cannot defend against a privileged database writer who recalculates hashes. It is an incremental integrity aid, not tamper-proof live financial accounting.
4. The paper trading PnL fixture is a simulation input, not reconciled broker evidence. Account currency conversion, institutional position risk, market correlation and real execution remain unimplemented.
5. The `P0` release gate remains BLOCKED, and the additive `WX` candidate has not obtained independent architectural admission. Do not promote any phase on unit test pass alone.

## Resume

Resolve Patrol registration via authorized privileged route, inspect the exact current Git heads and review gate contracts, bring up a Wolf-Coin-controlled worktree, then run qualified Tenfold source mutation and manual Cookpit source/build/host lanes. Keep the two domains financially segregated, preserve deterministic risk, and qualify trading/sports releases independently.

**Classification:** New first-light source candidate; update existing `CURRENT.md` / `PICKUP.md`. No change to protected main or real financial accounts.
