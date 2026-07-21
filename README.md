# Wolf-Coin

**Wolf-Coin is a self-sufficient, local-first, evidence-driven autonomous trading system.**

It is not a renamed forex bot, a wrapper around one external project, or an AI model with permission to place trades. Wolf-Coin combines deterministic market infrastructure, broker execution, strategy research, risk control, auditable multi-agent reasoning, recovery, scheduling, and owner control in one native repository.

> **Current status:** Architecture and implementation planning.
>
> **Default operating mode:** Research and paper trading only.
>
> **Live trading:** Locked until every release gate in the master plan is satisfied.

## Mission

Build one system that can:

1. collect and validate market data;
2. research and test strategies;
3. detect market regimes and trading opportunities;
4. challenge its own conclusions before acting;
5. enforce hard portfolio and account risk limits;
6. execute through broker and exchange adapters;
7. recover state after crashes, restarts, network loss, or provider failure;
8. explain every decision with evidence;
9. learn only from verified outcomes;
10. remain useful when every hosted AI provider is unavailable.

## Core doctrine

Wolf-Coin follows these rules:

- **Capital preservation before opportunity.**
- **Deterministic controls outrank model opinion.**
- **No trade is valid without an invalidation condition.**
- **No strategy reaches live capital directly from research.**
- **Backtests are evidence, not proof of future profitability.**
- **Paper trading is the default and live trading is an earned capability.**
- **Every order must be attributable to a versioned strategy and signed decision ledger.**
- **Every critical service must support restart recovery and idempotent reconciliation.**
- **AI may analyze, propose, challenge, and explain; hard risk controls retain veto power.**
- **External projects are research sources, not permanent runtime dependencies unless explicitly approved.**

## Intelligence model

Wolf-Coin adapts the strongest ideas from Sergeant's evidence-led officer system and OpenClaw's local-first autonomy model.

```text
Market data and account state
            ↓
Deterministic evidence pipeline
            ↓
Scout → Analyst → Strategist → Risk Officer → Execution Officer
            ↓                       ↑
        Challenger ────────────────┘
            ↓
Judge decision ledger
            ↓
Commander verdict
            ↓
BLOCK | PAPER | HUMAN APPROVAL | LIVE
```

The system must continue in deterministic safe mode when no language model is available. Models are replaceable reasoning engines beneath Wolf-Coin's own contracts; they are never the identity, source of truth, or final risk authority.

## Planned market coverage

The architecture is multi-market, but implementation will be staged:

1. **MetaTrader 5 forex and CFDs** — first execution target.
2. **Crypto spot and derivatives** — through a separate exchange-adapter contract.
3. **OANDA or another direct forex API** — removes exclusive dependence on a desktop MT5 terminal.
4. **Stocks, futures, and options** — only after the common portfolio and execution contracts are proven.

## Repository plan

```text
Wolf-Coin/
├── apps/                    # CLI, dashboard, API and optional messaging surfaces
├── wolf_core/               # domain models, configuration, events and shared contracts
├── wolf_gateway/            # daemon, scheduler, task ledger and health supervision
├── wolf_data/               # feeds, validation, storage and feature pipelines
├── wolf_markets/            # MT5, OANDA and crypto adapters
├── wolf_execution/          # orders, positions, reconciliation and recovery
├── wolf_guard/              # hard risk engine and kill switches
├── wolf_brain/              # deterministic decision flow and optional model routing
├── wolf_officers/           # specialist analysis and challenge roles
├── wolf_lab/                # backtesting, replay, walk-forward and paper simulation
├── wolf_strategies/         # versioned strategy packages and manifests
├── wolf_memory/             # decision ledgers, lessons and outcome attribution
├── wolf_observability/      # logs, metrics, traces, alerts and audit export
├── tests/                   # unit, contract, integration, replay and failure tests
├── research/                # external-source evaluations and experiment records
└── docs/                    # architecture, roadmap, policies and operating guides
```

The complete proposed layout and boundaries are documented in `docs/REPOSITORY_STRUCTURE.md`.

## Release modes

| Mode | Purpose | Orders |
|---|---|---|
| `RESEARCH` | Data analysis, strategy development and historical replay | None |
| `BACKTEST` | Deterministic historical simulation | Simulated |
| `PAPER` | Real-time market data with simulated capital | Simulated |
| `SHADOW` | Produces proposed live orders but cannot submit them | None |
| `APPROVAL` | Owner must approve every trade before submission | Live after approval |
| `GUARDED_LIVE` | Small, bounded live account under strict limits | Live |
| `LIVE` | Mature operation with all gates active | Live |
| `SAFE` | Manage existing risk only; block new exposure | Close/reduce only |
| `HALT` | Emergency stop and reconciliation | No new orders |

A mode transition is a signed state change with audit history. The system may automatically move toward safer modes, but it may never automatically promote itself into a riskier mode.

## Documentation

- [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) — complete product and engineering plan
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phased implementation and exit criteria
- [`docs/RISK_POLICY.md`](docs/RISK_POLICY.md) — hard risk doctrine and live-trading gates
- [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) — module boundaries and contracts
- [`docs/SOURCE_RESEARCH_MAP.md`](docs/SOURCE_RESEARCH_MAP.md) — what to study, adapt, reject, and attribute
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) — external code and attribution register

## First milestone

The first working milestone is deliberately modest:

- local daemon;
- SQLite state and event ledger;
- validated MT5 connection;
- market/account snapshots;
- deterministic risk engine;
- one simple strategy interface;
- historical replay;
- paper execution;
- restart recovery;
- structured decision ledger;
- CLI status, doctor, start, stop, reconcile, and emergency-halt commands.

No generative model is required for that milestone.

## Safety notice

Trading involves substantial risk. Wolf-Coin must never promise profit, hide drawdown, silently change strategy logic, or treat backtest results as guaranteed live performance. Use demo or paper accounts until the documented proof gates are satisfied, and use only capital that can be lost without threatening essential needs.
