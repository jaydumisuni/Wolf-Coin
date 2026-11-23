# Wolf-Coin KRATOS native paper preview — host evidence

**Date:** 2026-11-23
**Source commit built:** f2fe764cfd69676b5d521d3d823afb6d86133d07 (draft PR #10).
**Scope:** independent Linux research/paper preview; this is not P0–P12, WX-0–WX-10, MT5, broker, sportsbook or profit qualification.

## Patrol — self-service registration restored

- Canonical project root: `/home/kratos/projects/Wolf-Coin`, owner kratos, mode `0700`.
- Patrol `route` resolves to this root, `check` says `allow / registered project root`, Git is initialized and a separate feature worktree is under `.workspace/worktrees/`.
- Previous blocker: Oracle node has `NoNewPrivileges=true` and cannot elevate through inline `sudo`.
- Resolved via the existing authorized Oracle root helper without asking the owner for a terminal command. Fix permanently integrated into installed Patrol `main` commit `257f78dbf75c20576d6fa7d9d30aa111372fc2ed`. See Patrol `docs/PROJECT_ROOT_PRIVILEGE_RECOVERY.md`.
- Patrol targeted and boundary regression tests: **45 passed**. Existing normal sudo workflow is preserved, unauthorized/malformed helpers fail closed. No security relaxation and no user-visible password handling.

## Native installed runtime

- Source: feature HEAD `f2fe764cfd69676b5d521d3d823afb6d86133d07`.
- Build: offline pip wheel (no network dependencies), `wolf_coin_core-0.1.0a0-py3-none-any.whl`.
- Wheel SHA-256: `a99589dcd248424c45e04e6c85171cb22aa38f6663c233d40802d9c973a3ad46`.
- Installed package: `/home/kratos/.local/share/wolf-coin-paper/releases/f2fe764cfd69676b5d521d3d823afb6d86133d07/venv` (outside source checkout).
- State: `/home/kratos/.local/state/wolf-coin-paper/paper.sqlite3` (mode `0600`).
- Native user service: `wolf-coin-paper-preview.service`, enabled with `NoNewPrivileges=true`. The runtime is pinned to the versioned installed wheel and doesn't import code from a project worktree.
- Loopback listener: `127.0.0.1:18766`, chosen to preserve existing unrelated services occupying ports 8765 and 18765. Both `/sports` and `/trading` returned HTTP 200; `/health` reported `PAPER` with `live_enabled=false`; POST returned HTTP 405.
- Virtual sports paper account: ZMW 100. Virtual trading paper account: ZMW 100. These are not real funds. `wolf doctor` reported two accounts, four ledger events, zero execution adapters and `live_enabled=false`.
- KRATOS exact source test: **31 passed** on Python 3.14.4.
- Cookpit manually invoked source/host micro **PASS** and heavy **PASS**, pinned to `f2fe764cfd69676b5d521d3d823afb6d86133d07`. Receipts: `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-kratos-paper-host/evidence`. No new GPT supervisor, recurring schedule or automatic financial task.

## Tenfold and release truth

Tenfold Gen1's durable 24-node campaign is at `/home/kratos/projects/Tenfold/.workspace/wolf-coin-20261123/tenfold-authority.db`. P0 was moved from `BLOCKED` to `READY` following the verified Patrol registration, but **zero phase gates are PROVEN**, no execution leases or source implementation tasks are completed by that transition.

This is the *first usable local research/paper console*, not autonomous sports betting or trading, not a qualified ML strategy, and not permission for real-money deposits. Strategy/data sources, sustained paper evaluation, provider contracts, hardware/restart drills, independently validated risk and product release still require implementation.

## Launch and recovery

As long as KRATOS is running and the user service is active, open these local pages on KRATOS:

- Sports: `http://127.0.0.1:18766/sports`
- Trading: `http://127.0.0.1:18766/trading`

Status command: `systemctl --user status wolf-coin-paper-preview.service`. Read-only health: `curl http://127.0.0.1:18766/health`. Stop/start use the ordinary owner-level systemd user unit (no root required). Never use the old port 8765 without checking service ownership.

Before a future source upgrade, keep the old release installed for rollback, run tests and Cookpit host verification on the exact new artifact, then update the user service to the pinned new installed path. Keep all real-money effects disabled until independent trading and sports qualification.
