# Wolf-Coin — KRATOS paper funding-preview installation proof

**Date:** 2026-11-23. **State:** PAPER INSTALLED; REAL FUNDING NOT ADMITTED.
**Frozen source artifact:** commit `b01d2691f023366fcfc64bfa819beeac72746161`, Wolf-Coin draft PR #10.
**Wheel:** `wolf_coin_core-0.1.0a1-py3-none-any.whl` SHA-256 `f8b360c7266b974692bd33cbab33480642cc3da57758e39d2f4ae7b99f8c5340`.
**Build:** offline, no new runtime dependencies, verified package contains funding CLI, provider review, FX math, historical lab and dashboard.

## Host acceptance

- Pinned Python virtualenv at `/home/kratos/.local/share/wolf-coin-paper/releases/b01d2691f023366fcfc64bfa819beeac72746161/venv`.
- user systemd `wolf-coin-paper-preview.service`: active and enabled, `NoNewPrivileges=true`. Previous service unit backed up at `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/paper-preview-upgrade-20261123/old.service`.
- Previous working wheel release `f2fe764cfd69676b5d521d3d823afb6d86133d07` retained for rollback; paper database unchanged.
- Loopback only, `127.0.0.1:18766`; GET `/health`, `/sports`, `/trading`, `/funding` and `/api/funding-readiness` all returned HTTP 200 after versioned service replacement.
- `/health` reports PAPER, no live or remote service; real-money API routes are absent; POST to funding readiness/trading returns HTTP 405.
- `/api/funding-readiness` reports both domains: `funding_permitted=false`, `max_customer_deposit_authorized_ZMW=0`, `transfer_adapters=0`. Virtual pilot account balances are not bank or broker funds.
- Brave on KRATOS opened three local views in the graphical user session (sports, trading, funding).
- Source run: **187/187 tests passed**, Python 3.14 on KRATOS. Package `wolf-funding-readiness` itself verified after isolated installation. Existing ledger `wolf doctor` verified two virtual accounts/four prior journal events, zero execution adapters and no live mode.
- Research data retained only under local `.workspace/research/openfootball-20261123/`; exact file source hashes and 380/380 chronological holdout comparison recorded in `docs/FUNDING_AND_PROVIDER_DILIGENCE_2026-11-23.md`. Raw historical data were not committed to this public repository.

## Authority and remaining qualifications

This evidence establishes a native, loopback-only, reproducible **paper pilot and funding-readiness DISPLAY**, not eligibility to deposit or access real sportsbook/broker accounts. It does not establish the software's predictive edge, real-time feeds, operator permission, actual MT5 account, provider fees/FX or production release.

The Tenfold durable campaign remains 24 unproven gates, with P0 READY for construction. Manual Cookpit engineering evidence is retained in `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-funding-candidate/evidence/` and must remain bound to exact source generation. No GPT supervisor was added.

## Resume

1. Verify Patrol registration and exact committed source.
2. Verify user service source pin, rollback unit, read-only health and funding API.
3. Review funding/provider diligence and collect independently approved provider/accounts, without taking passwords in chat.
4. Qualify broker demo and sport operator API terms, min executable size and costs; run sustained live-price paper/shadow and incident/recovery review.
5. Sign separate final owner-funded policy after independent gate acceptance; then and only then design and install a narrowly scoped live effect adapter.

**Current operator decision: DO NOT DEPOSIT.**
