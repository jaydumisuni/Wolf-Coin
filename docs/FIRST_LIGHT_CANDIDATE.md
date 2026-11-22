# First-light deterministic candidate (P0/P1 + WX-2/3/5 groundwork)

Status: experimental code candidate, unadmitted and uninstalled on KRATOS.

Scope: Python 3.11+ standard-library source containing UTC/Decimal/scope contracts, a transactional SQLite append journal with optimistic revision fencing, paper account balances, football 1X2 odds and a paper risk-only verdict. There are **no** broker, sportsbook, network, browser, funding, real-money, daemon or background execution capabilities. No autonomous prediction has been proven.

This is not P0 completion. Python support, Windows/MT5 dependency viability, tooling, source licensing, independent approval, and the native KRATOS host remain open acceptance obligations. A verified unit test on this candidate is not a physical KRATOS/Windows or real-account proof.

Important limits: the ledger hash chain is not anchored externally and cannot defend against an attacker with database-write access who recalculates hashes. Cashout, currency conversion and trading broker state are not yet implemented. An eligible paper risk verdict is an **advisory** result and is not a bookmaker placement instruction. Real financial effects have no execution path in this source.
