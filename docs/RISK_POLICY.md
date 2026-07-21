# Wolf-Coin Risk Policy

**Status:** Foundational policy 1.0  
**Applies to:** Research, paper, shadow, approval, guarded-live, and live operation  
**Principle:** No model, strategy, operator surface, or broker adapter may bypass this policy.

---

## 1. Purpose

This document defines the hard safety boundary for Wolf-Coin. Initial numerical values are conservative defaults and must remain configurable by account and mode, but every change requires an auditable owner decision.

The risk engine is deterministic. Language models may explain risk, identify additional concerns, or recommend a safer action, but they cannot increase a limit, waive a rule, or reinterpret a rejection as approval.

## 2. Risk modes

### Research

No broker connection capable of order submission is required. Market and account data may be historical or read-only.

### Backtest

Only simulated orders. Results must include transaction costs, spread, slippage assumptions, and drawdown.

### Paper

Real-time data with simulated capital. The same `OrderIntent`, risk checks, decision ledger, and management state machine intended for live operation must be used.

### Shadow

A live broker may be connected read-only or with trading disabled. Wolf-Coin creates broker-normalized proposals but cannot submit them.

### Approval

Every trade requires explicit authenticated owner approval after the final size and broker-normalized request are known.

### Guarded live

Live trading with the smallest practical capital allocation and the strictest limits. Only approved symbols, strategies, sessions, and order types are allowed.

### Live

Broader approved operation, still bounded by hard risk limits.

### Safe

No new exposure. Wolf-Coin may cancel pending orders, tighten or restore protective stops when policy permits, close or reduce positions, and reconcile state.

### Halt

No automated order action except an explicitly authenticated emergency-close instruction. All scheduled strategy activity stops.

## 3. Non-negotiable prohibitions

Wolf-Coin must block:

- orders without a versioned strategy or authorized manual intent;
- live orders without a decision ledger;
- new exposure when account or broker identity is uncertain;
- new exposure when required market data is stale or contradictory;
- new exposure after a critical reconciliation failure;
- lot sizes below or above broker constraints;
- prices, stops, or targets invalid for the broker symbol;
- orders that exceed any applicable hierarchy limit;
- use of withdrawal-enabled crypto credentials where a restricted key is available;
- hidden martingale or loss-recovery sizing;
- unlimited grid expansion;
- doubling after losses as an automatic policy;
- averaging into a losing position unless an explicitly approved bounded strategy defines the full maximum exposure before the first order;
- removal of a protective stop merely to avoid realizing a loss;
- automatic promotion into a more permissive operating mode;
- model-generated raw broker commands.

## 4. Initial conservative defaults

These are starting defaults for guarded live, not promises of suitability. They must be reviewed against account size, broker contract specifications, and strategy behavior.

| Limit | Guarded-live default | Live maximum without new owner approval |
|---|---:|---:|
| Risk per trade | 0.25% of current equity | 0.50% |
| Aggregate open modeled risk | 0.75% of equity | 2.00% |
| Daily realized + modeled loss stop | 1.00% | 2.00% |
| Weekly loss stop | 2.50% | 4.00% |
| Peak-to-trough account drawdown stop | 5.00% | 8.00% |
| Concurrent positions | 2 | 5 |
| Same currency/underlying cluster | 0.50% modeled risk | 1.00% |
| Same strategy aggregate | 0.50% modeled risk | 1.50% |
| Maximum consecutive losses before cooldown | 3 | 4 |
| Minimum reward-to-risk at initial target | Strategy-specific, normally ≥ 1.2 | Strategy-specific |
| Maximum spread | Instrument/session profile | Instrument/session profile |
| Maximum expected slippage | Instrument/order profile | Instrument/order profile |

A lower mode-specific or strategy-specific limit always wins.

## 5. Position sizing

### 5.1 Required inputs

Sizing requires:

- verified account equity and currency;
- instrument contract specification;
- entry price or bounded entry range;
- protective stop price;
- expected spread and slippage;
- commission and financing model where material;
- existing exposure;
- selected risk percentage or absolute risk cap;
- broker volume minimum, maximum, and step.

If any required input is unavailable or invalid, sizing fails closed.

### 5.2 Maximum modeled loss

The risk calculation must include at least:

```text
price loss to stop
+ entry spread
+ expected slippage
+ commission
+ adverse rounding allowance
```

For instruments with gap risk or nonlinear payoff, the model must add an appropriate stress component. The nominal stop loss is not automatically the true maximum loss.

### 5.3 Rounding

Volume is rounded down to the broker step unless a documented algorithm proves another result remains within the risk cap. Rounding may never increase modeled loss beyond the approved cap.

### 5.4 Split orders

Split entries or take-profit legs must be evaluated as one risk group. Creating several small tickets does not create several separate risk allowances.

## 6. Portfolio exposure

Wolf-Coin must aggregate exposure by:

- instrument;
- quote and base currency;
- underlying asset;
- direction;
- strategy;
- broker account;
- correlation group;
- event sensitivity where configured.

Examples:

- Long EURUSD and long EURJPY both create long EUR exposure.
- Long XAUUSD across two strategies remains one gold risk cluster.
- Several crypto perpetual positions may share broad market beta even when symbols differ.

The portfolio officer and deterministic risk engine must evaluate the combined state before every new order and significant amendment.

## 7. Correlation and concentration

Initial implementation may use configured groups before statistical correlation is mature. Later versions may combine:

- static economic relationships;
- rolling return correlation;
- common currency exposure;
- common underlying or sector;
- strategy signal correlation;
- tail-event co-movement.

A statistical model cannot be the sole protection. Unknown correlation is treated conservatively rather than as zero.

## 8. Spread, liquidity, and slippage guards

Every instrument has a session-aware execution profile containing:

- normal spread distribution;
- hard maximum spread;
- expected slippage bands by order type;
- minimum liquidity or tick activity where measurable;
- restricted rollover periods;
- broker maintenance windows;
- event-specific restrictions.

New orders are blocked when:

- spread exceeds the hard limit;
- market data is stale;
- quote movement is discontinuous beyond the allowed entry model;
- estimated slippage invalidates the trade thesis or risk cap;
- the symbol is not tradeable;
- the market is closing too soon for the strategy's minimum holding assumptions.

## 9. Protective exits

### 9.1 Broker-side protection

Guarded-live and live positions should use broker-side protective stops whenever the venue supports them. Client-only stops require explicit approval and a stronger operational-risk allowance.

### 9.2 Stop movement

A stop may move only according to a versioned management rule. It may not be widened to avoid a loss unless the original strategy explicitly defines a bounded dynamic stop and the resulting maximum risk remains within the original approved cap.

### 9.3 Breakeven and trailing

Breakeven and trailing logic must account for spread, commission, and actual fills. “Breakeven” means nonnegative expected net result after costs, not simply the entry quote.

### 9.4 Time exits

Strategies with time assumptions must define a maximum holding period or reassessment schedule. Abandoned positions without active management are a policy violation.

## 10. Daily and weekly stops

Daily loss includes:

- realized losses;
- fees and financing;
- current modeled loss on open positions;
- unresolved execution discrepancies where conservative treatment is required.

When a daily stop triggers:

1. all new exposure is blocked;
2. pending entry orders are cancelled unless cancellation is unsafe or impossible;
3. current positions are reviewed under reduce-only policy;
4. mode downgrades to `SAFE`;
5. an incident and owner alert are created;
6. resumption requires the configured next-session reset plus any required owner review.

A weekly or drawdown stop requires explicit owner reactivation after analysis.

## 11. Loss streak and anomaly cooldowns

A cooldown may be triggered by:

- consecutive losses;
- performance significantly below the strategy's validated distribution;
- abnormal slippage;
- repeated broker rejection;
- repeated stale data;
- unexpected position mismatch;
- model or strategy disagreement beyond threshold;
- sudden spread or volatility regime change;
- strategy drift detection.

Cooldowns suspend the affected strategy, instrument, adapter, or entire system according to scope. They do not erase history or reset statistics.

## 12. Economic-event policy

The first implementation uses configurable restricted windows around high-impact events. A strategy must explicitly declare whether it is:

- prohibited during event windows;
- permitted only to manage existing positions;
- designed and validated for event trading.

If the economic-calendar source is required but unavailable, event-sensitive strategies fail closed.

## 13. Data-risk policy

New exposure is blocked when critical data fails checks for:

- freshness;
- ordering;
- duplicates;
- missing intervals;
- invalid OHLC values;
- symbol identity;
- timezone;
- severe cross-source divergence;
- feature-computation errors.

Existing positions enter a management policy using the safest reliable source available. Uncertainty is surfaced rather than hidden.

## 14. Execution-risk policy

Every live request must include:

- decision ID;
- order-intent ID;
- idempotency key;
- account ID;
- canonical and broker symbol;
- side and order type;
- normalized volume;
- price constraints;
- stop and target policy;
- expiration where applicable;
- maximum acceptable slippage;
- risk approval token or record reference.

Unknown, ambiguous, or contradictory broker responses enter `UNKNOWN` and force reconciliation. Wolf-Coin must not retry blindly.

## 15. Reconciliation policy

Reconciliation is required:

- at startup;
- after broker reconnect;
- after an unknown submission result;
- periodically while live;
- after order or position events;
- before moving out of safe mode;
- before shutdown where possible.

Any unmatched live order or position is treated as an incident. New exposure is blocked until its origin and management policy are resolved.

## 16. Model-risk policy

Model-assisted analysis must:

- receive only the minimum necessary data;
- identify its provider, model, and prompt or task version;
- return typed output;
- cite ledger evidence IDs rather than inventing observations;
- declare uncertainty and missing evidence;
- remain advisory unless a deterministic contract explicitly consumes a bounded field;
- never receive broker secrets;
- never choose a risk limit higher than the deterministic maximum;
- never submit or amend a live order directly.

Model failure must not disable stop supervision, reconciliation, risk checks, or emergency controls.

## 17. Strategy-risk policy

Every strategy manifest must define:

- supported instruments and timeframes;
- required data and features;
- market-regime assumptions;
- entry conditions;
- invalidation and exit rules;
- maximum expected holding period;
- sizing model;
- whether scaling or multiple entries are allowed;
- maximum total group exposure;
- event policy;
- session policy;
- known failure modes;
- validated parameter range;
- promotion stage;
- owner-approved live scope.

Unknown parameters or out-of-range configuration block activation.

## 18. Manual commands

Manual trading commands are not exempt. They pass through account verification, broker validation, risk limits, and audit. High-impact commands require explicit confirmation using the final normalized values.

Emergency halt always remains available to an authenticated owner.

## 19. Mode transition controls

A mode promotion requires:

- authenticated owner action;
- proof-gate status;
- clean reconciliation;
- active risk policy;
- healthy broker and data adapters;
- recorded account and allocation scope;
- recorded strategy and symbol allowlists;
- expiry or review date where configured.

Automatic systems may demote mode immediately when safety requires it.

## 20. Incident severity

### Critical

Uncontrolled exposure, account mismatch, duplicate live order, missing protection, corrupted state affecting live positions, unauthorized command, or inability to determine live position truth.

Action: halt or safe mode, immediate owner alert, no new exposure.

### High

Repeated reconciliation failures, daily stop, abnormal drawdown, severe stale data, repeated broker rejection, or management task failure.

Action: safe mode for affected scope or whole system.

### Medium

Single recoverable adapter failure, unusual slippage, strategy drift warning, or delayed scheduled analysis.

Action: suspend or investigate affected capability.

### Low

Optional model, chart, narrative, or secondary notification failure.

Action: continue with degraded noncritical functionality.

## 21. Proof required before guarded live

At minimum:

- clean demo-account reconciliation across restarts;
- idempotency proof under timeouts and repeated requests;
- broker-side protective-stop proof;
- daily stop and emergency halt tests;
- stale-data and disconnected-broker veto tests;
- partial-fill and rejection handling;
- spread and slippage calibration;
- paper and shadow evidence;
- full audit trail;
- dedicated bounded allocation;
- owner-signed live limits.

## 22. Policy change process

Every change must record:

- old and new value or rule;
- justification;
- affected modes, accounts, instruments, and strategies;
- expected risk impact;
- test and replay evidence;
- reviewer decision;
- owner approval when live behavior changes;
- effective time;
- rollback plan.

Policy history is immutable and queryable.
