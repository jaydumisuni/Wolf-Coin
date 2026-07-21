# Wolf-Coin Master Plan

**Document status:** Foundational plan 1.0  
**Repository:** `jaydumisuni/Wolf-Coin`  
**Primary objective:** Build a self-sufficient, evidence-driven autonomous trading system whose intelligence increases analytical depth without weakening deterministic risk control.

---

## 1. Executive intent

Wolf-Coin will be one native system for research, backtesting, live market observation, paper trading, guarded execution, account supervision, recovery, reporting, and verified learning.

The project will borrow ideas and, where licensing permits, carefully adapted implementation patterns from mature trading frameworks, MetaTrader projects, Sergeant, OpenClaw, and other open-source systems. It will not become a loose bundle of cloned repositories. Every accepted capability must be translated into Wolf-Coin's own contracts, tests, safety boundaries, attribution records, and operational language.

The intelligence target is not “an AI that predicts markets.” The target is a disciplined machine that:

- acquires trustworthy evidence;
- distinguishes observation from inference;
- compares multiple explanations;
- quantifies uncertainty;
- refuses action when evidence is weak or operational state is unsafe;
- records why it acted or refused;
- attributes outcomes to the correct strategy and market conditions;
- improves only after reproducible validation.

## 2. Success definition

Wolf-Coin is successful when it can run locally for long periods and demonstrate all of the following:

1. deterministic market and account state reconstruction;
2. reproducible backtests with transaction costs and no look-ahead leakage;
3. paper-trading parity with the live execution path;
4. strict portfolio-level risk enforcement independent of models;
5. broker reconnection and order reconciliation after restart;
6. explainable decision ledgers for every proposed and executed trade;
7. safe degradation when data, broker, network, storage, or AI providers fail;
8. strategy promotion based on measured evidence rather than intuition;
9. owner-visible health, exposure, decisions, errors, and overrides;
10. complete code provenance and license compliance.

Profit is not an engineering acceptance criterion. Reliability, bounded risk, reproducibility, and truthful reporting are.

## 3. Non-goals

Wolf-Coin will not initially attempt to:

- guarantee profit;
- discover a universal strategy that works in every market regime;
- permit an LLM to bypass risk checks or submit arbitrary broker commands;
- use martingale, unlimited averaging, or loss-recovery sizing as a default;
- optimize only for backtest return;
- trade every supported market immediately;
- copy opaque binaries or code without compatible licensing and provenance;
- modify its own live strategy code without review, testing, and owner approval;
- promote itself from paper to live mode automatically;
- depend on one model provider, one broker, or one communication channel.

## 4. Operating doctrine

### 4.1 Authority hierarchy

The authority order is:

1. emergency owner halt;
2. hard risk policy;
3. broker and account truth;
4. verified market data;
5. deterministic strategy rules;
6. decision-ledger reconciliation;
7. model-assisted analysis;
8. narrative explanation.

A lower layer cannot override a higher layer.

### 4.2 Safety direction

Wolf-Coin may move automatically from a riskier state to a safer state:

```text
LIVE → GUARDED_LIVE → APPROVAL → SHADOW → PAPER → SAFE → HALT
```

It may never automatically move in the opposite direction.

### 4.3 Evidence classes

Every material fact in a trade decision receives a class:

- **Observed:** directly retrieved from broker, exchange, validated feed, or local state.
- **Calculated:** deterministically derived from observed data.
- **Inferred:** interpretation from a strategy, statistical model, or officer.
- **Assumed:** configured value or unresolved approximation.
- **Unavailable:** required evidence could not be obtained.

Critical evidence may not silently fall back from observed to assumed.

### 4.4 Fail-closed versus fail-open

Wolf-Coin fails closed for:

- new order submission;
- position-size calculation;
- account identity mismatch;
- stale or contradictory market data;
- missing stop loss where policy requires one;
- corrupted decision or execution state;
- unknown broker response;
- daily or portfolio risk breaches.

It may fail open only for noncritical features such as optional commentary, visual charts, or secondary model analysis.

## 5. System architecture

Wolf-Coin is organized into seven planes.

### 5.1 Control plane

Responsibilities:

- daemon lifecycle;
- configuration resolution;
- scheduler;
- task ownership;
- health supervision;
- mode transitions;
- owner commands;
- feature flags;
- secrets references;
- audit of privileged actions.

Primary modules: `wolf_gateway`, `apps`, `wolf_core`.

### 5.2 Data plane

Responsibilities:

- tick and candle acquisition;
- economic and market-event inputs;
- broker account snapshots;
- validation and normalization;
- time alignment;
- duplicate detection;
- feature computation;
- durable storage;
- replay datasets;
- data-quality scoring.

Primary modules: `wolf_data`, market-adapter data interfaces.

### 5.3 Decision plane

Responsibilities:

- deterministic strategy evaluation;
- market regime classification;
- specialist officer packets;
- challenge and contradiction search;
- uncertainty scoring;
- final Judge ledger;
- Commander verdict;
- explanation generation.

Primary modules: `wolf_brain`, `wolf_officers`, `wolf_strategies`.

### 5.4 Risk plane

Responsibilities:

- position sizing;
- exposure aggregation;
- account and portfolio drawdown;
- concentration and correlation limits;
- spread and slippage checks;
- market-hours and event restrictions;
- stale-data veto;
- loss streak and abnormal-behavior detection;
- mode downgrade and kill switch.

Primary module: `wolf_guard`.

The risk plane runs in-process with the execution request and independently as a supervisor. A cached prior approval is never enough to submit a later order.

### 5.5 Execution plane

Responsibilities:

- order-intent validation;
- broker-native normalization;
- idempotency keys;
- order submission;
- acknowledgement tracking;
- fill and rejection processing;
- stop and take-profit management;
- reconciliation;
- restart recovery;
- reduce-only and emergency actions.

Primary modules: `wolf_execution`, `wolf_markets`.

### 5.6 Laboratory plane

Responsibilities:

- historical replay;
- backtesting;
- walk-forward analysis;
- Monte Carlo and perturbation tests;
- paper simulation;
- shadow comparison;
- parameter experiments;
- strategy registry and promotion evidence.

Primary modules: `wolf_lab`, `research`.

### 5.7 Observability and memory plane

Responsibilities:

- structured logs;
- metrics and traces;
- decision ledgers;
- execution journals;
- incident records;
- model and strategy attribution;
- verified lessons;
- owner reports;
- tamper-evident export.

Primary modules: `wolf_memory`, `wolf_observability`.

## 6. Native intelligence architecture

### 6.1 Officer formation

Wolf-Coin adapts Sergeant's specialist and challenge architecture into market roles.

#### Market Scout

Collects market, account, session, spread, volatility, liquidity, and event evidence. It does not recommend a trade.

#### Technical Analyst

Computes approved features and describes price structure. It must distinguish calculations from interpretation.

#### Regime Officer

Classifies conditions such as trend, range, volatility expansion, volatility compression, illiquidity, or event risk. It returns confidence and conflicting evidence.

#### Strategy Officer

Evaluates only versioned, enabled strategies against the current evidence. It cannot invent an unregistered live strategy.

#### Portfolio Officer

Examines existing positions, currency exposure, correlated instruments, account margin, and proposed concentration.

#### Risk Officer

Calculates permitted risk and independently verifies stop distance, size, expected loss, spread, slippage allowance, and policy limits.

#### Execution Officer

Checks broker symbol state, order type, price precision, minimum distance, volume step, trade permissions, and idempotency.

#### Challenger

Attempts to falsify the proposal. It searches for stale data, contradictory timeframes, event risk, regime mismatch, overfitting signals, abnormal spread, correlated exposure, and operational uncertainty.

#### Judge

Reconciles all packets into a canonical decision ledger. It does not average votes blindly. Hard blockers, missing required evidence, and risk-policy failures dominate.

#### Commander

Returns one verdict:

- `BLOCK`
- `OBSERVE`
- `PAPER`
- `REQUEST_APPROVAL`
- `EXECUTE`
- `REDUCE_RISK`
- `ENTER_SAFE_MODE`
- `HALT`

### 6.2 Deterministic-first behavior

Every officer has a deterministic baseline. Optional statistical or language models may enrich specific questions, but the system must remain capable of:

- collecting data;
- evaluating explicit strategies;
- sizing risk;
- blocking unsafe orders;
- reconciling positions;
- managing stops;
- reporting state;
- entering safe mode;

without any model endpoint.

### 6.3 Model router

The optional model router supports:

- local models first when configured;
- explicit hosted endpoints;
- provider and model fallbacks;
- cooldowns after transient failures;
- strict owner-pinned sessions;
- per-task timeouts and token budgets;
- complete provider/model attribution;
- redaction of secrets and unnecessary account identifiers;
- schema validation of every model response.

Model output is untrusted input. It must pass typed parsing, evidence-reference checks, and policy validation.

### 6.4 High-intelligence decision rules

“High intelligence” in Wolf-Coin means depth and quality, not unchecked autonomy. The decision engine will:

1. consider multiple market hypotheses;
2. seek disconfirming evidence;
3. identify missing information;
4. estimate uncertainty;
5. compare expected reward with realistic costs and adverse movement;
6. evaluate portfolio consequences rather than one chart alone;
7. distinguish setup quality from execution quality;
8. preserve unresolved disagreement in the ledger;
9. reduce size or abstain as uncertainty rises;
10. learn from outcomes only after proper attribution.

## 7. Canonical decision ledger

Every proposed trade creates an immutable decision record containing at least:

- decision ID and timestamp;
- run, session, account, broker, and environment IDs;
- instrument and asset class;
- strategy ID, version, code hash, and parameter hash;
- operating mode;
- market-data snapshot references;
- data-quality score and freshness;
- session and economic-event state;
- technical and regime evidence;
- alternative hypotheses;
- officer packets;
- Challenger findings;
- unresolved questions;
- expected spread and slippage;
- entry, invalidation, stop, target, and time-exit rules;
- proposed position size and maximum modeled loss;
- portfolio impact before and after;
- risk-rule evaluations;
- final verdict and reason codes;
- owner approval where required;
- resulting order-intent ID;
- execution acknowledgement and fills;
- later management decisions;
- final outcome and attribution.

No live order may exist without a ledger that can be traced to it.

## 8. Strategy lifecycle

Strategies move through a controlled registry.

### Stage A — Idea

A human or research agent records the hypothesis, expected market behavior, invalidation logic, required data, and risks.

### Stage B — Implemented research strategy

The strategy is typed, versioned, deterministic for identical inputs, and accompanied by unit tests.

### Stage C — Historical validation

Required checks include:

- clean data and timestamp audit;
- no look-ahead bias;
- transaction cost and spread modeling;
- in-sample versus out-of-sample separation;
- parameter sensitivity;
- benchmark comparison;
- regime breakdown;
- maximum drawdown and tail losses;
- trade-count adequacy;
- reproducible report artifact.

### Stage D — Walk-forward and perturbation

The strategy must survive rolling windows, parameter perturbation, spread inflation, slippage, delayed entry, missing ticks, and altered starting dates.

### Stage E — Paper trading

The real-time paper path must use the same decision, risk, and order-intent contracts as live trading.

### Stage F — Shadow mode

Wolf-Coin observes live broker conditions and creates proposed orders but does not submit them. Differences between theoretical and broker-valid execution are measured.

### Stage G — Approval mode

Every live trade requires owner approval. Account size, symbols, sessions, and risk are tightly restricted.

### Stage H — Guarded live

Small capital, minimal risk per trade, low daily loss limit, limited concurrent positions, and automatic downgrade on anomalies.

### Stage I — Mature live

Granted only after sustained evidence. It remains reversible and bounded.

### Retirement

Strategies are automatically suspended, not deleted, when drift, drawdown, execution divergence, or data incompatibility breaches policy. Reactivation requires new evidence and approval.

## 9. Research ingestion from external repositories

Every external source follows this pipeline:

```text
Discover
  ↓
License and provenance check
  ↓
Threat and quality review
  ↓
Capability extraction
  ↓
Native design decision
  ↓
Clean implementation or attributed adaptation
  ↓
Unit and contract tests
  ↓
Replay and failure testing
  ↓
Documented acceptance or rejection
```

The research record must state:

- source repository and exact commit;
- license;
- files reviewed;
- concept or code accepted;
- code copied or rewritten;
- attribution obligations;
- security concerns;
- known limitations;
- Wolf-Coin tests proving the accepted capability;
- final decision.

No opaque executable, undocumented strategy, credential-bearing file, or profit claim is accepted as evidence.

## 10. Market adapters

### 10.1 Common adapter contract

Every broker or exchange adapter implements:

- connect and authenticate;
- health and capability discovery;
- account snapshot;
- symbol metadata;
- market data subscription and polling;
- historical data retrieval;
- order validation;
- submit, amend, cancel, and close;
- open orders and positions;
- trade history;
- reconciliation cursor;
- normalized error classification;
- rate-limit and reconnect behavior.

### 10.2 MT5 first

The first adapter targets MetaTrader 5 because the forex-bot research set provides useful Python and MQL5 patterns. The MT5 design must support:

- Windows terminal dependency isolation;
- terminal and account identity verification;
- symbol alias mapping;
- asynchronous command orchestration;
- automatic reconnect with bounded backoff;
- broker lot, price, stop-distance, and trading-session rules;
- Expert Advisor bridge only where direct Python functionality is insufficient;
- crash-safe reconciliation;
- demo account first.

### 10.3 Broker independence

Domain strategies may never import MT5, OANDA, or exchange-specific classes. They consume normalized market and portfolio interfaces. Broker-native details are resolved only in adapters and execution validation.

## 11. Data architecture

### 11.1 Storage tiers

- **SQLite:** configuration snapshots, task ledger, strategy registry, decisions, orders, positions, audit, and small local deployments.
- **Parquet:** candles, ticks, features, replay datasets, and research outputs.
- **Optional PostgreSQL/Timescale:** later multi-node or high-volume deployment.
- **Object storage:** compressed historical archives, reports, and backups.

### 11.2 Time and identity

All internal timestamps use UTC with source timestamp, receive timestamp, and processing timestamp preserved. Every entity has stable IDs. Symbol aliases are mapped to canonical instruments.

### 11.3 Data-quality gates

Checks include:

- stale timestamps;
- nonmonotonic ordering;
- duplicate bars or ticks;
- missing intervals;
- impossible OHLC relationships;
- abnormal spreads;
- timezone ambiguity;
- price-scale changes;
- broker-symbol remapping;
- cross-source divergence.

Data failing critical checks cannot drive new exposure.

## 12. Risk architecture

Risk is hierarchical:

1. order-level;
2. position-level;
3. instrument-level;
4. currency or underlying exposure;
5. strategy-level;
6. account-level;
7. portfolio-level;
8. operational and infrastructure risk.

The complete initial doctrine is in `docs/RISK_POLICY.md`.

Mandatory capabilities include:

- fixed-fraction or volatility-aware risk sizing;
- maximum modeled loss before submission;
- hard daily and total drawdown limits;
- maximum concurrent positions;
- concentration and correlation checks;
- spread and slippage thresholds;
- session and economic-event restrictions;
- loss-streak cooldown;
- stale-data and disconnected-broker veto;
- reduce-only safe mode;
- emergency halt;
- owner-controlled live unlock.

## 13. Execution and recovery

### 13.1 Order intent

Strategies produce an `OrderIntent`, never a broker call. The intent contains normalized desired behavior. Risk and execution transform it into a broker-valid request.

### 13.2 Idempotency

Every order intent has an idempotency key derived from decision ID, strategy version, instrument, side, and intent sequence. Retries must not duplicate exposure.

### 13.3 State machine

```text
PROPOSED
  → RISK_REJECTED
  → APPROVAL_PENDING
  → APPROVED
  → SUBMITTING
  → ACKNOWLEDGED
  → PARTIALLY_FILLED
  → FILLED
  → MANAGING
  → CLOSING
  → CLOSED

Any state may enter UNKNOWN, RECONCILING, FAILED, or CANCELLED where valid.
```

### 13.4 Restart recovery

At startup Wolf-Coin must:

1. load the last durable state;
2. connect to the broker;
3. verify account identity;
4. retrieve open orders, positions, and recent history;
5. match broker objects to local intents;
6. flag ambiguous or orphaned objects;
7. restore management tasks;
8. enter `SAFE` when reconciliation is incomplete;
9. prohibit new exposure until the reconciliation verdict is clean.

### 13.5 Network loss

Existing broker-side stops should protect positions when the local daemon is unavailable. Wolf-Coin must not depend exclusively on client-side stops for live risk control.

## 14. Scheduler and autonomy

Wolf-Coin adapts OpenClaw's durable scheduler concepts into a narrow trading scheduler.

Job types:

- market-session open and close;
- candle-close strategy runs;
- economic-calendar refresh;
- broker and data health checks;
- account reconciliation;
- position supervision;
- daily risk reset;
- report generation;
- dataset maintenance;
- backup verification;
- strategy evaluation;
- owner notifications.

Requirements:

- persistent job definitions and run history;
- no duplicate concurrent run for the same exclusive task;
- deadlines and timeouts;
- bounded retries with error classification;
- task heartbeats;
- lost-task reconciliation;
- dependency checks;
- isolated research jobs;
- explicit tool permissions;
- audit of every scheduled privileged action.

## 15. Security model

### 15.1 Secrets

- No broker, exchange, model, or messaging secrets in Git.
- Secrets are loaded from environment variables or an approved local secret store.
- API keys use minimum permissions.
- Crypto exchange keys must have withdrawals disabled.
- Logs and reports redact credentials and sensitive identifiers.
- Secret access is scoped by component.

### 15.2 Command boundaries

Natural-language input never maps directly to raw broker calls. Commands pass through:

1. authenticated owner identity;
2. command parser;
3. typed intent;
4. authorization policy;
5. risk policy;
6. explicit confirmation for high-impact actions;
7. audit logging.

### 15.3 External code

Research code is never executed directly on a machine containing live credentials. It is reviewed and tested in an isolated environment first.

### 15.4 Supply chain

- dependency lockfiles;
- hashes where supported;
- vulnerability scanning;
- license scanning;
- pinned CI actions;
- signed release artifacts later;
- reproducible clean installation proof.

## 16. Observability

Wolf-Coin must make unsafe silence impossible.

Required signals:

- daemon and adapter health;
- data freshness and quality;
- account equity, balance, margin, and drawdown;
- open exposure by instrument, currency, strategy, and correlation group;
- strategy evaluation counts and verdicts;
- proposed, blocked, approved, submitted, filled, rejected, and reconciled orders;
- risk veto reasons;
- broker latency, spread, and slippage;
- scheduler delays and failures;
- model-provider usage and failures;
- mode transitions and owner overrides;
- state-recovery status.

Alerts are severity classified and deduplicated. A critical safety alert cannot be suppressed by a model.

## 17. Interfaces

### CLI first

Initial commands:

```text
wolf init
wolf doctor
wolf start
wolf stop
wolf status
wolf mode show
wolf mode set <mode>
wolf broker status
wolf data status
wolf risk status
wolf strategies list
wolf strategies inspect <id>
wolf replay run <scenario>
wolf paper start
wolf decisions list
wolf decision show <id>
wolf reconcile
wolf safe
wolf halt
wolf resume
```

### Local API

A versioned local API exposes typed read and command endpoints. Privileged endpoints require authentication, authorization, and audit.

### Dashboard

The dashboard follows the control-plane state, not a separate source of truth. It shows health, modes, decisions, exposure, risk limits, strategy evidence, jobs, incidents, and approvals.

### Messaging

Telegram, WhatsApp, or other channels are optional notification and approval surfaces. They cannot bypass the local authorization and risk pipeline.

## 18. Testing doctrine

### Unit tests

Domain calculations, sizing, indicators, validation, state transitions, and error classification.

### Contract tests

Every adapter runs against the same market and execution contract suite.

### Integration tests

SQLite, scheduler, daemon, data pipeline, paper broker, MT5 demo bridge, API, and recovery.

### Historical replay tests

Known scenarios such as trend, gap, spread spike, flash move, stale feed, duplicate tick, broker rejection, partial fill, and restart during active position management.

### Failure injection

- network interruption;
- broker timeout;
- delayed acknowledgement;
- duplicated event;
- corrupted local cache;
- storage lock;
- model failure;
- clock skew;
- process crash;
- stale scheduler ownership;
- unexpected open position.

### Property-based tests

Risk invariants, lot normalization, price rounding, state-machine legality, idempotency, and reconciliation.

### Security tests

Secret redaction, command authorization, path and input validation, dependency checks, and untrusted-source isolation.

## 19. Release gates

A release cannot advance to the next operating mode unless all required gates pass.

### Research to backtest

- strategy manifest complete;
- deterministic execution;
- unit tests pass;
- data requirements defined;
- no prohibited sizing or hidden averaging.

### Backtest to paper

- reproducible out-of-sample report;
- realistic cost model;
- parameter sensitivity acceptable;
- drawdown within research policy;
- failure and edge-case tests pass;
- independent review complete.

### Paper to shadow

- sustained real-time stability;
- zero unexplained orders;
- restart recovery proven;
- account and data reconciliation clean;
- observability complete.

### Shadow to approval

- broker validation parity measured;
- spread and slippage model calibrated;
- no critical incident unresolved;
- owner accepts instrument, session, and risk scope.

### Approval to guarded live

- dedicated small account or bounded allocation;
- withdrawal-disabled credentials where applicable;
- broker-side stop protection;
- emergency halt tested;
- live limits signed by owner;
- automatic downgrade tested;
- backup and restore proven.

### Guarded live to live

- sufficient sample across multiple market conditions;
- drawdown and execution within policy;
- no unresolved reconciliation failures;
- strategy drift checks operating;
- owner explicitly promotes mode.

## 20. Governance and change control

Changes affecting live behavior require:

- issue or decision record;
- stated risk impact;
- tests;
- replay evidence;
- review;
- version change;
- migration plan where state changes;
- rollback plan;
- owner approval for policy or live-mode changes.

Strategy code, risk rules, and execution adapters are independently versioned. A strategy may not silently inherit changed risk behavior without a recorded compatibility decision.

## 21. Initial technology direction

The first implementation should favor clarity and local operability:

- Python 3.12 or a deliberately selected supported version;
- `asyncio` for orchestration;
- Pydantic or equivalent typed schemas;
- SQLite with explicit migrations;
- Parquet for market datasets;
- FastAPI for the local API;
- Typer or Click for CLI;
- pytest plus property-based tests;
- structured JSON logging;
- optional local model endpoints through OpenAI-compatible protocols;
- MQL5 bridge only for functionality that cannot be safely achieved through the selected MT5 interface.

The project must avoid forcing a Python version solely because a reference repo chose it. Version selection occurs during Phase 0 after MT5 and dependency compatibility testing.

## 22. First vertical slice

The first vertical slice proves the architecture end to end:

1. start the local daemon;
2. initialize SQLite state;
3. connect to an MT5 demo account;
4. retrieve and validate EURUSD candles and account state;
5. run one simple deterministic strategy in research mode;
6. create a decision ledger;
7. apply hard risk rules;
8. submit only to a paper broker;
9. manage the simulated position;
10. restart during the position;
11. reconcile and continue management;
12. produce a complete report.

No LLM, messaging channel, complex strategy, or live order is required. This slice proves that the spine is sound before intelligence layers are added.

## 23. Definition of self-sufficient

Wolf-Coin is self-sufficient when:

- its core runtime does not require Sergeant or OpenClaw installations;
- every required trading function has a native Wolf-Coin contract;
- it can operate in deterministic safe mode without hosted AI;
- state, schedules, decisions, and recovery are local and durable;
- at least one broker adapter and paper broker are fully supported;
- its own doctor, test, replay, and proof commands verify operation;
- external components are optional adapters or documented dependencies, not hidden architecture;
- the owner can inspect, stop, reconcile, and recover it without a model.

## 24. Immediate implementation order

1. repository standards and package skeleton;
2. core domain schemas and event ledger;
3. configuration and secret references;
4. SQLite migrations and task ledger;
5. daemon, CLI, health, and doctor;
6. paper broker and deterministic clock;
7. market-data contracts and validation;
8. risk engine;
9. decision ledger and officer contracts;
10. strategy registry and first example strategy;
11. historical replay and paper execution;
12. MT5 adapter and demo reconciliation;
13. failure injection and proof suite;
14. dashboard and local API;
15. optional local-model analysis;
16. shadow and approval modes;
17. guarded live only after gate evidence.

The detailed phase breakdown and exit criteria are in `docs/ROADMAP.md`.
