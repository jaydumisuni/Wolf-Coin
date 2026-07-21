# Wolf-Coin Implementation Roadmap

**Planning model:** Evidence-gated delivery  
**Rule:** A phase is complete only when its exit evidence exists. Calendar dates do not override missing proof.

---

## Program structure

Wolf-Coin will be built as a sequence of vertical capabilities. Each phase must produce something executable, inspectable, and testable. Complex intelligence is added only after the deterministic spine is reliable.

### Parallel workstreams

- **Core:** schemas, events, configuration, storage, lifecycle.
- **Markets:** data and broker/exchange adapters.
- **Risk:** deterministic policy and portfolio controls.
- **Execution:** order state, reconciliation, and recovery.
- **Lab:** replay, backtesting, paper, and strategy evidence.
- **Intelligence:** officer packets, challenge, Judge, and optional models.
- **Operations:** scheduler, doctor, observability, API, dashboard, alerts.
- **Assurance:** testing, security, provenance, CI, releases.

## Phase 0 — Decisions, standards, and proof harness

### Objective

Remove foundational ambiguity before implementation begins.

### Deliverables

- Select supported Python version after testing MT5 and critical dependencies.
- Define package manager and lockfile policy.
- Establish formatting, linting, type checking, testing, and security tools.
- Add repository contribution and review rules.
- Define architecture decision record template.
- Define research-source evaluation template.
- Define evidence artifact directory and naming.
- Create CI with path-aware jobs to conserve Actions minutes.
- Add a minimal proof command that reports environment and test status.
- Record the initial licensing decision for Wolf-Coin itself.

### Required decisions

- Monorepo package layout.
- Sync versus async boundaries.
- Pydantic or equivalent schema library.
- SQLite migration tool.
- Logging format.
- Exact MT5 integration path for first experiments.
- Local API authentication approach.
- Whether the public repo can contain every future component or needs private deployment overlays.

### Exit evidence

- Clean install on the target Windows development machine.
- Clean install in Linux CI for broker-independent modules.
- Formatting, lint, type, test, and dependency checks pass.
- Architecture and risk docs accepted as current source of truth.

## Phase 1 — Core domain and durable event ledger

### Objective

Create the common language that every component must use.

### Deliverables

- Domain IDs and UTC timestamp policy.
- Typed schemas for:
  - account;
  - instrument;
  - quote, tick, and candle;
  - strategy manifest;
  - signal and setup;
  - decision ledger;
  - order intent;
  - broker order;
  - fill;
  - position;
  - risk evaluation;
  - task and run;
  - incident;
  - operating-mode transition.
- Append-oriented event ledger in SQLite.
- Explicit migrations.
- Configuration layering and validation.
- Secret references without secret persistence.
- Stable serialization and schema-version rules.
- Deterministic clock abstraction.

### Tests

- Schema round trips.
- Invalid-state rejection.
- UTC and ordering invariants.
- Migration upgrade and rollback tests.
- Concurrent write behavior.
- Event replay reconstructs expected state.

### Exit evidence

- A fixture account, market, decision, and paper order can be written, replayed, and reconstructed deterministically.

## Phase 2 — Gateway, scheduler, health, and operator CLI

### Objective

Give Wolf-Coin an always-on local body before adding trading behavior.

### Deliverables

- Local daemon lifecycle.
- Single-instance ownership lock.
- Durable scheduler and task history.
- Task heartbeat, timeout, bounded retry, and lost-task recovery.
- Component health registry.
- Mode state machine.
- Privileged action audit.
- Graceful shutdown.
- CLI commands:
  - `wolf init`;
  - `wolf doctor`;
  - `wolf start`;
  - `wolf stop`;
  - `wolf status`;
  - `wolf mode show/set`;
  - `wolf tasks list/show`;
  - `wolf safe`;
  - `wolf halt`.
- Local structured logs.

### Failure tests

- Duplicate daemon launch.
- Forced process termination.
- Overdue task after restart.
- Task timeout.
- Storage lock.
- Invalid configuration.
- Clock jump.

### Exit evidence

- A scheduled deterministic task survives daemon restart without duplicate execution.
- `wolf doctor` distinguishes healthy, degraded, unsafe, and blocked states.

## Phase 3 — Paper broker and execution state machine

### Objective

Prove order lifecycle and recovery without external broker risk.

### Deliverables

- Common broker adapter contract.
- Deterministic paper broker.
- Market, limit, stop, and stop-limit intent support as appropriate.
- Broker capability declarations.
- Order validation.
- Idempotency keys.
- Partial fills, rejections, cancellations, and expirations.
- Position accounting.
- Commission, spread, and slippage simulation.
- Execution state machine.
- Reconciliation between local intent and paper-broker truth.
- Restart recovery.

### Tests

- Duplicate submit request creates one order.
- Timeout followed by retry does not duplicate exposure.
- Partial fill and cancellation accounting.
- Gap through stop.
- Rejection after validation race.
- Restart at every order state.
- Orphan-order detection.

### Exit evidence

- Complete order and position histories reconstruct exactly after restart and replay.

## Phase 4 — Data acquisition, validation, and replay storage

### Objective

Create trusted data before evaluating strategies.

### Deliverables

- Common market-data adapter contract.
- Canonical instrument registry and broker alias mapping.
- Candle and tick ingestion.
- Parquet datasets with manifests.
- Data-quality scoring.
- Detection for duplicates, gaps, invalid OHLC, stale data, ordering, timezone, scale, and divergence.
- Feature pipeline contract.
- Historical replay clock.
- Dataset provenance and checksums.
- Initial EURUSD and one additional instrument dataset.

### Tests

- Deliberately corrupted datasets.
- Duplicate and out-of-order events.
- Missing candles.
- DST and timezone transitions.
- Cross-source disagreement.
- Replay determinism.

### Exit evidence

- Identical replay inputs produce identical normalized events and feature values.

## Phase 5 — Deterministic risk engine

### Objective

Implement the non-bypassable safety authority.

### Deliverables

- Risk-policy configuration by mode, account, strategy, and instrument.
- Position sizing with realistic modeled loss.
- Broker volume-step normalization.
- Order, instrument, currency, strategy, account, and portfolio exposure.
- Daily, weekly, and total drawdown controls.
- Concurrent-position limits.
- static correlation groups, with extension point for dynamic correlation;
- spread, slippage, market-hours, data-freshness, and event guards;
- loss-streak and anomaly cooldowns;
- safe-mode and halt triggers;
- immutable risk evaluation records.

### Property tests

- Approved size never exceeds risk cap after rounding.
- Splitting an order never creates additional risk allowance.
- Unknown correlation never reduces measured exposure.
- Lower-scoped limit always wins.
- Any critical missing input blocks new exposure.

### Exit evidence

- A proof suite demonstrates that strategies, models, CLI commands, and adapters cannot bypass risk rejection.

## Phase 6 — Strategy registry and laboratory

### Objective

Create a scientific path from idea to paper candidate.

### Deliverables

- Versioned strategy manifest.
- Strategy parameter schema and validated range.
- Strategy package discovery.
- First simple reference strategy, chosen for testability rather than profitability.
- Backtest engine using the same decision and order contracts as paper mode.
- Transaction-cost, spread, slippage, and financing models.
- Out-of-sample and walk-forward runner.
- Parameter sensitivity reports.
- Monte Carlo trade-order and cost perturbation.
- Regime breakdown.
- Benchmark comparison.
- Reproducible report bundle.
- Strategy stage transitions and suspension.

### Anti-overfitting checks

- No hidden future data.
- Purged or properly separated validation windows where needed.
- Minimum trade count and duration policies.
- Neighboring-parameter performance.
- Multiple starting dates.
- Inflated cost tests.
- Delayed execution tests.

### Exit evidence

- The first reference strategy can be independently replayed from a report manifest and produces the same result.

## Phase 7 — Native decision officers and challenge ledger

### Objective

Add high-intelligence structure without requiring a language model.

### Deliverables

- Officer packet schema.
- Market Scout.
- Technical Analyst.
- Regime Officer.
- Strategy Officer.
- Portfolio Officer.
- Risk Officer.
- Execution Officer.
- Challenger.
- Judge reconciliation.
- Commander verdict.
- Reason codes and unresolved-evidence tracking.
- Canonical decision-ledger persistence.
- Configurable decision depth:
  - `fast`;
  - `adaptive`;
  - `deep`;
  - `maximum`.

### Tests

- Hard blocker defeats majority approval.
- Missing required evidence remains unresolved.
- Contradictory timeframes are preserved.
- Challenger can block but cannot fabricate broker truth.
- Judge output is deterministic for deterministic packets.
- Every order intent traces to one decision.

### Exit evidence

- Paper trading produces complete, queryable decision ledgers and meaningful refusal reasons.

## Phase 8 — MT5 demo adapter

### Objective

Connect the native system to real broker conditions without live capital.

### Deliverables

- MT5 terminal connection and identity verification.
- Account and symbol snapshots.
- Historical and live market data.
- Order check and broker normalization.
- Demo order submission.
- Open order, position, and history retrieval.
- Reconnect and bounded backoff.
- Error classification.
- Symbol alias mapping.
- Volume, precision, stop-distance, and session constraints.
- Restart reconciliation.
- Position management.
- Optional MQL5 bridge only for proven gaps in direct integration.

### Tests

- Wrong account or server.
- Terminal stopped and restarted.
- Network loss.
- Broker rejection.
- Price movement between validation and submit.
- Partial fill where supported.
- Existing manual position.
- Broker comment changes.
- Unknown submit result.
- Terminal upgrade or symbol metadata change.

### Exit evidence

- Demo positions survive Wolf-Coin restart and are reconciled without duplicate orders or missing management.

## Phase 9 — Real-time paper, shadow, and operational proof

### Objective

Run continuously under real market timing before any live order.

### Deliverables

- Real-time paper execution using MT5 data.
- Shadow broker-normalized proposals.
- Session-aware scheduler.
- Economic-event adapter and policy.
- Operational metrics and alerts.
- Daily and weekly reports.
- Decision-to-outcome attribution.
- Incident workflow.
- Backup and restore.
- Long-run soak tests.

### Measurements

- uptime;
- data freshness;
- scheduling delay;
- decision latency;
- proposal count;
- veto reasons;
- spread and slippage estimates;
- broker normalization differences;
- restart and reconnect count;
- unexplained state count;
- paper-versus-shadow divergence.

### Exit evidence

- Sustained operation with zero unexplained order or position state and complete incident closure.

## Phase 10 — Optional model intelligence and local-first routing

### Objective

Use models to deepen analysis and explanation while retaining deterministic authority.

### Deliverables

- OpenAI-compatible model adapter.
- Local endpoint discovery limited to approved local addresses.
- Explicit remote endpoint configuration.
- Provider/model fallback chains and cooldowns.
- Per-officer prompt and schema versions.
- Evidence-ID grounding.
- Secret and sensitive-data redaction.
- Timeout and output budgets.
- Model attribution in decision ledgers.
- Deterministic fallback behavior.
- Offline mode.
- Tests against malformed, speculative, contradictory, and unavailable model output.

### Initial model tasks

- summarize officer evidence;
- generate alternative hypotheses;
- identify potential missing evidence;
- explain risk vetoes;
- produce owner-readable reports;
- assist research classification.

Models do not initially control entries, sizing, or live execution.

### Exit evidence

- Turning every model off changes explanation depth but does not break safe operation or deterministic strategy results.

## Phase 11 — Local API, dashboard, and approval surfaces

### Objective

Give the owner full visibility and bounded control.

### Deliverables

- Versioned local API.
- Authentication and role policy.
- Dashboard for:
  - health;
  - mode;
  - account and exposure;
  - strategies;
  - decisions;
  - risk limits;
  - tasks;
  - incidents;
  - approvals;
  - reports.
- Approval flow showing final broker-normalized values.
- Telegram or WhatsApp alert adapter.
- Notification deduplication.
- Read-only remote status option.
- Audit for every command and approval.

### Security tests

- replayed approval;
- expired approval;
- modified order after approval;
- unauthorized channel sender;
- lost or duplicated message;
- API rate limiting;
- secret leakage;
- unsafe remote exposure.

### Exit evidence

- An owner can understand, approve, reject, halt, and reconcile from the control surface without bypassing local policy.

## Phase 12 — Guarded-live readiness

### Objective

Prove that the system is safe enough for a deliberately tiny, bounded live experiment.

### Required evidence package

- all critical tests pass;
- independent review of risk and execution code;
- clean-clone installation proof;
- reproducible release artifact;
- demo restart and reconciliation evidence;
- idempotency proof;
- broker-side protection proof;
- emergency halt drill;
- backup restore drill;
- paper and shadow performance report;
- calibrated spread and slippage profiles;
- no unresolved critical or high incident;
- dedicated account or bounded allocation;
- explicit owner-signed live policy;
- approved symbol, strategy, session, and order-type allowlists;
- rollback and manual intervention guide.

### Initial guarded-live restrictions

- one broker account;
- one or two instruments;
- one independently reviewed strategy;
- approval mode first;
- minimum practical risk;
- low concurrent-position cap;
- no grid, martingale, or unbounded scaling;
- broker-side stop required;
- automatic daily stop;
- automatic safe-mode downgrade on anomalies.

### Exit evidence

- The owner explicitly authorizes the guarded-live experiment. There is no automatic promotion.

## Post-12 roadmap

Only after the MT5 spine is mature:

- OANDA or direct forex API adapter;
- crypto spot adapter;
- crypto derivatives under separate policy;
- market-data redundancy;
- dynamic portfolio correlation;
- advanced regime and statistical models;
- multi-account allocation;
- distributed worker nodes;
- mobile companion;
- stocks, futures, and options;
- controlled strategy discovery agents;
- signed strategy bundles;
- formal audit export.

## Global definition of done

A capability is not done because a happy-path demo works. It is done when:

- contracts are documented;
- errors are classified;
- tests include failure behavior;
- restart behavior is known;
- observability exists;
- security and secrets are considered;
- migration and rollback are defined;
- provenance and licensing are recorded;
- user-facing claims match implementation;
- proof artifacts are reproducible.
