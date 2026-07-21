# Wolf-Coin Repository Structure

This document defines the planned native module boundaries. The goal is to prevent broker details, model providers, strategy code, and risk authority from becoming tangled.

```text
Wolf-Coin/
├── apps/
│   ├── cli/                         # operator commands
│   ├── api/                         # local HTTP API
│   ├── dashboard/                   # owner command center
│   └── messaging/                   # optional Telegram/WhatsApp adapters
│
├── wolf_core/
│   ├── ids.py                       # stable identifiers
│   ├── clock.py                     # real and replay clocks
│   ├── config.py                    # typed layered configuration
│   ├── events.py                    # canonical domain events
│   ├── errors.py                    # normalized error taxonomy
│   ├── modes.py                     # operating-mode state machine
│   ├── authz.py                     # command authorization contracts
│   ├── serialization.py             # versioned durable encoding
│   └── models/                      # domain schemas only
│       ├── account.py
│       ├── instrument.py
│       ├── market.py
│       ├── strategy.py
│       ├── decision.py
│       ├── risk.py
│       ├── execution.py
│       ├── portfolio.py
│       ├── task.py
│       └── incident.py
│
├── wolf_gateway/
│   ├── daemon.py                    # local process lifecycle
│   ├── scheduler.py                 # durable scheduling
│   ├── task_ledger.py               # ownership, retries, history
│   ├── health.py                    # component health registry
│   ├── supervisor.py                # restart/degrade policy
│   ├── commands.py                  # typed privileged commands
│   └── locks.py                     # single-instance/exclusive tasks
│
├── wolf_storage/
│   ├── sqlite.py                    # transactional state store
│   ├── migrations/                  # explicit schema migrations
│   ├── repositories/                # domain persistence interfaces
│   ├── parquet.py                   # market/research datasets
│   ├── backup.py                    # snapshot and restore
│   └── retention.py                 # safe cleanup policies
│
├── wolf_data/
│   ├── contracts.py                 # feed adapter interfaces
│   ├── ingestion.py                 # ticks/candles/events
│   ├── validation.py                # data-quality gates
│   ├── normalization.py             # symbols, time, precision
│   ├── features.py                  # deterministic feature pipeline
│   ├── quality.py                   # scoring and incident creation
│   ├── replay.py                    # historical event stream
│   └── sources/                     # provider-specific data adapters
│
├── wolf_markets/
│   ├── contracts.py                 # broker/exchange adapter contract
│   ├── paper/                       # deterministic paper broker
│   ├── mt5/                         # MetaTrader 5 adapter
│   ├── oanda/                       # future direct forex adapter
│   └── crypto/                      # future exchange adapters
│
├── wolf_execution/
│   ├── intent.py                    # normalized OrderIntent handling
│   ├── validation.py                # pre-submit checks
│   ├── idempotency.py               # duplicate prevention
│   ├── state_machine.py             # order lifecycle
│   ├── submitter.py                 # adapter submission orchestration
│   ├── positions.py                 # normalized position management
│   ├── protection.py                # SL/TP and management contracts
│   ├── reconciliation.py            # broker/local truth matching
│   ├── recovery.py                  # startup/reconnect restoration
│   └── emergency.py                 # reduce-only and emergency paths
│
├── wolf_guard/
│   ├── policy.py                    # resolved policy hierarchy
│   ├── sizing.py                    # risk-based volume calculation
│   ├── exposure.py                  # portfolio aggregation
│   ├── correlation.py               # static/dynamic group analysis
│   ├── spread.py                    # spread/liquidity guards
│   ├── slippage.py                  # expected/observed slippage
│   ├── drawdown.py                  # daily/weekly/peak controls
│   ├── events.py                    # economic-event restrictions
│   ├── anomalies.py                 # drift/loss/rejection cooldowns
│   ├── verdict.py                   # non-bypassable risk decision
│   └── kill_switch.py               # safe and halt transitions
│
├── wolf_strategies/
│   ├── contracts.py                 # strategy input/output contract
│   ├── registry.py                  # versions and promotion stage
│   ├── manifest.py                  # declared assumptions and limits
│   ├── reference/                   # deliberately simple examples
│   └── approved/                    # later owner-approved strategies
│
├── wolf_officers/
│   ├── contracts.py                 # officer packet schema
│   ├── scout.py
│   ├── technical.py
│   ├── regime.py
│   ├── strategy.py
│   ├── portfolio.py
│   ├── risk.py
│   ├── execution.py
│   ├── challenger.py
│   ├── judge.py
│   └── commander.py
│
├── wolf_brain/
│   ├── mission.py                   # decision-run orchestration
│   ├── evidence.py                  # evidence classes and references
│   ├── decision_ledger.py           # canonical decision creation
│   ├── depth.py                     # fast/adaptive/deep/maximum
│   ├── model_router.py              # optional provider routing
│   ├── grounding.py                 # validates evidence references
│   ├── schemas.py                   # model response schemas
│   └── explain.py                   # owner-readable explanations
│
├── wolf_lab/
│   ├── backtest.py
│   ├── paper.py
│   ├── shadow.py
│   ├── walk_forward.py
│   ├── perturbation.py
│   ├── monte_carlo.py
│   ├── benchmarks.py
│   ├── regimes.py
│   ├── costs.py
│   ├── reports.py
│   └── promotion.py
│
├── wolf_memory/
│   ├── decisions.py                 # durable ledgers
│   ├── outcomes.py                  # trade and strategy attribution
│   ├── lessons.py                   # verified lessons only
│   ├── incidents.py
│   └── audit.py
│
├── wolf_observability/
│   ├── logging.py
│   ├── metrics.py
│   ├── tracing.py
│   ├── alerts.py
│   ├── reports.py
│   └── redaction.py
│
├── research/
│   ├── sources/                     # source evaluations by repo/commit
│   ├── experiments/                 # reproducible experiment manifests
│   ├── datasets/                    # metadata only; large data ignored
│   ├── reports/                     # generated research evidence
│   └── rejected/                    # reasons concepts were not accepted
│
├── tests/
│   ├── unit/
│   ├── property/
│   ├── contract/
│   ├── integration/
│   ├── replay/
│   ├── failure/
│   ├── security/
│   └── proof/
│
├── scripts/                         # deterministic developer/operator scripts
├── docs/
├── pyproject.toml
├── README.md
└── THIRD_PARTY_NOTICES.md
```

## Dependency direction

The allowed dependency direction is intentionally strict:

```text
apps
  ↓
gateway / brain / lab
  ↓
execution / guard / officers / strategies / data
  ↓
market contracts / storage repositories
  ↓
core domain
```

Rules:

- `wolf_core` imports no broker, database, framework, UI, or model-provider modules.
- Strategies import normalized domain and feature contracts, never MT5 or exchange SDKs.
- Broker adapters do not decide strategy or risk policy.
- Model-provider adapters do not import execution submitters.
- UI and messaging surfaces never write directly to broker adapters or storage tables.
- Risk verdicts are consumed by execution, not reconstructed by it.
- Storage implementations satisfy repository interfaces; domain logic does not embed SQL.

## Core contracts

### `MarketDataAdapter`

Must expose normalized historical and live market events plus health and capability information.

### `BrokerAdapter`

Must expose account, symbol, order, position, history, validation, submission, cancellation, close, and reconciliation functions with normalized errors.

### `Strategy`

Consumes a declared evidence snapshot and returns a typed candidate setup or abstention. It does not submit orders or calculate final broker volume.

### `RiskEngine`

Consumes the decision candidate, portfolio state, broker metadata, and resolved policy. Returns an immutable approval or rejection with reason codes and permitted normalized risk.

### `ExecutionService`

Consumes only approved order intents and broker state. It owns idempotency, submission, acknowledgement, and state transitions.

### `Officer`

Consumes an evidence packet and returns a typed, attributable specialist packet. It cannot mutate account or execution state.

### `Judge`

Reconciles officer packets, deterministic blockers, and unresolved evidence into one canonical ledger.

### `Scheduler`

Runs registered typed tasks; it does not accept arbitrary model-generated shell commands in live deployments.

## Event boundaries

Recommended durable events include:

- `MarketSnapshotAccepted`
- `MarketDataRejected`
- `AccountSnapshotAccepted`
- `StrategyEvaluated`
- `OfficerPacketRecorded`
- `DecisionFinalized`
- `RiskApproved`
- `RiskRejected`
- `OwnerApprovalRequested`
- `OwnerApprovalGranted`
- `OrderIntentCreated`
- `OrderSubmissionStarted`
- `BrokerAcknowledged`
- `OrderPartiallyFilled`
- `OrderFilled`
- `OrderRejected`
- `PositionOpened`
- `ProtectionUpdated`
- `PositionClosed`
- `ReconciliationStarted`
- `ReconciliationCompleted`
- `ReconciliationFailed`
- `ModeChanged`
- `RiskLimitTriggered`
- `IncidentOpened`
- `IncidentResolved`

Events should contain references and normalized facts, not unbounded raw payloads. Raw broker responses may be stored separately with redaction and checksum references.

## Configuration hierarchy

Highest precedence first:

1. emergency owner command;
2. runtime safety downgrade;
3. account-specific policy;
4. mode policy;
5. strategy live scope;
6. instrument profile;
7. application defaults.

Configuration resolving to an unsafe or contradictory state fails startup or disables the affected capability.

## Plugin boundary

Future broker, feed, model, strategy, and notification plugins must register through typed entry points. Plugin discovery never grants permissions automatically. Each plugin declares:

- identity and version;
- capabilities;
- configuration schema;
- required secrets;
- allowed network targets;
- operating modes;
- health checks;
- license and provenance;
- test status.

## Deployment boundary

The first supported deployment is one local machine with:

- Wolf-Coin daemon;
- SQLite state;
- local Parquet storage;
- MT5 terminal on Windows;
- optional local model server;
- local API bound to loopback by default.

Multi-node execution is a later capability. The first design must not add distributed-system complexity before one-node recovery is proven.
