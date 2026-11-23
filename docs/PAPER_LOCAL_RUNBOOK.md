# Wolf-Coin: local research/paper pilot runbook

**Current installed state (2026-11-23):** Patrol is registered. The packaged paper-only preview is running as systemd user unit `wolf-coin-paper-preview.service` at `http://127.0.0.1:18766/sports` and `/trading` (port 8765 belongs to another service). No owner command is needed to initialize Patrol. See `docs/KRATOS_PAPER_HOST_PROOF_2026-11-23.md`. The older setup procedure below is retained as historical/recovery reference; do not rerun initialization over the already-registered project.

**Qualification:** first-light candidate only. No financial API, dealer connection, automation, trained prediction model or live bankroll transfer. Source has been locally verified in an isolated Python environment; KRATOS Patrol registration and native installation remain outstanding.

## Patrol registration (run in an authorized KRATOS interactive terminal)

The standard Oracle terminal carries `NoNewPrivs: 1`; sudo cannot create a new root-owned Projects child from that session. Do not disable Patrol or relocate Wolf-Coin into another project. The approved setup is:

```sh
patrol init-project Wolf-Coin --remote https://github.com/jaydumisuni/Wolf-Coin.git
```

After successful registration, fetch the reviewed source candidate:

```sh
cd /home/kratos/projects/Wolf-Coin
git remote add origin https://github.com/jaydumisuni/Wolf-Coin.git
git fetch origin
git switch --track -c work/wx-tenfold-cookpit-20261123 origin/work/wx-tenfold-cookpit-20261123
```

If an origin already exists, check that it matches instead of adding another. Do **not** merge the draft branch into `main` before its independent review.

## Native Python environment (no Docker)

```sh
python3 -m venv .workspace/venv
.workspace/venv/bin/python -m pip install -e .
.workspace/venv/bin/python -m pytest -q
```

If `pytest` is missing, install development test dependencies in this isolated environment according to the project's accepted dependency policy; do not claim a test pass before the actual command succeeds.

## Virtual paper accounts

```sh
W=.workspace/venv/bin
DB=.workspace/wolf-paper.sqlite3
$W/wolf-paper --db "$DB" --domain sports --account pilot-1 init
$W/wolf-paper --db "$DB" --domain trading --account pilot-1 init
$W/wolf-paper --db "$DB" --domain sports --account pilot-1 deposit --amount 100 --event-id initial-sports
$W/wolf-paper --db "$DB" --domain trading --account pilot-1 deposit --amount 100 --event-id initial-trading
$W/wolf-paper --db "$DB" --domain sports --account pilot-1 status
$W/wolf-paper --db "$DB" odds --home 2.0 --draw 3.5 --away 4.0
$W/wolf doctor --db "$DB"
```

`deposit` and `withdraw` here modify **virtual test balances only**. The odds command only normalizes manually entered prices, identifies the feed as unverified and refuses execution. An event ID must not be reused for another operation. `freeze` intentionally cannot reactivate a paper account.

## Two local browser views

```sh
.workspace/venv/bin/wolf-dashboard --db .workspace/wolf-paper.sqlite3 --account pilot-1 --port 8765
```

Open two tabs on KRATOS:

- `http://127.0.0.1:8765/sports`
- `http://127.0.0.1:8765/trading`

The dashboard binds **only** to loopback, accepts GET, has no state-changing endpoint, cannot submit a bet/order and displays `NO LIVE EXECUTION`. Close it with Ctrl+C. This is not an autonomous supervisor or financial daemon.

## Gate status

Source fixture tests alone do not satisfy P0's Windows compatibility/clean install gate, P2's restartable scheduler, P3's paper execution state, P8's broker bridge, WX-8's sustained paper evidence or separate real-money release gates. No live-money action is authorized. Opening browser tabs does not start autonomous trading or betting.
