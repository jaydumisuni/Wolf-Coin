# Wolf-Coin Source Research Map

This document controls how Wolf-Coin studies and borrows from external and THETECHGUY repositories. It is a planning map, not permission to copy code blindly.

## Acceptance rule

For every source, Wolf-Coin must capture the exact repository commit, license, files reviewed, security concerns, accepted ideas, rejected ideas, attribution, and native tests before implementation is merged.

There are three reuse classes:

- **Concept study:** understand architecture or behavior, then implement natively without copying protected expression.
- **Attributed adaptation:** adapt compatible licensed code and preserve required notices.
- **Direct dependency:** use a maintained package through a narrow adapter after dependency, supply-chain, and license review.

Direct dependency is the exception, not the default.

---

## 1. THETECHGUY internal and sibling systems

### `jaydumisuni/Sergeant`

**Role in Wolf-Coin:** Evidence discipline, specialist formation, challenge, reconciliation, verdicts, proof gates, and truthful reporting.

**Study and adapt:**

- deterministic evidence before model analysis;
- specialist officer packets;
- Challenger and Judge separation;
- unsupported high-severity claim rejection;
- adaptive/deep/maximum investigation depth;
- model-agnostic local and configured routes;
- explicit degraded operation when models are unavailable;
- proof-suite and final-proof mindset;
- evidence locker and audit trail concepts;
- claims-must-match-implementation doctrine.

**Do not copy blindly:**

- software-review-specific scanners;
- IDE interfaces unrelated to trading;
- naming that would confuse Wolf-Coin's own product identity;
- assumptions that human review is always available at trading-event speed.

**Native Wolf-Coin result:** Market, Strategy, Portfolio, Risk, Execution, Challenger, Judge, and Commander contracts with decision-ledger evidence references.

### `jaydumisuni/openclaw`

**Role in Wolf-Coin:** Always-on local gateway, durable scheduler, task recovery, provider fallback, isolated agents, channel adapters, doctor commands, and local-first operation.

**Study and adapt:**

- daemon installation and lifecycle concepts;
- durable scheduled jobs and run history;
- task timeout, cleanup, and lost-task reconciliation;
- model and auth-profile fallback with cooldowns;
- session isolation and bounded tool permissions;
- local-first gateway and remote-exposure caution;
- onboarding and doctor workflows;
- multi-channel notification architecture;
- health and recovery behavior.

**Do not copy blindly:**

- general-purpose unrestricted tool execution;
- a giant channel surface before core trading is reliable;
- arbitrary agent-authored unattended shell scripts in live mode;
- full assistant session semantics where deterministic trading tasks are sufficient;
- secrets or user-specific runtime state.

**Native Wolf-Coin result:** A narrow trading gateway with typed scheduled tasks, explicit permissions, no model-generated raw shell execution in live deployments, and deterministic safe operation.

### `jaydumisuni/hunter`, `hunter-foreman`, and related orchestration repos

**Role:** Later integration points for local models, owner reasoning, ecosystem status, and development workflow.

**Policy:** Wolf-Coin owns its runtime and does not require Hunter to trade safely. Hunter may consume Wolf-Coin APIs, produce research assistance, or explain decisions through approved interfaces.

---

## 2. Forex and MT5 research

### GitHub `forex-bot` topic

**Role:** Discovery surface for MT5, OANDA, strategy, indicator, broker, and automation patterns.

**Policy:** Topic inclusion, stars, screenshots, backtest curves, and recent repository creation are not quality proof. Each candidate must pass license, history, code, test, security, and realism review.

### `Ichinga-Samuel/aiomql`

**Current advertised license:** MIT; verify exact file and commit before adaptation.

**Study and potentially adapt:**

- async wrappers around MT5 calls;
- automatic reconnection;
- strategy and trader separation;
- concurrent multi-symbol orchestration;
- session windows;
- risk and money-management abstractions;
- position trackers;
- SQLite/JSON/CSV result recording;
- task queue and state store;
- sync mirrors for scripts and notebooks.

**Concerns:**

- current Python and Windows requirements must be validated;
- configuration examples contain direct credentials and should not define Wolf-Coin secret design;
- risk abstractions require independent review;
- framework behavior must be tested against actual broker edge cases.

**Native result:** MT5 adapter and orchestration patterns behind Wolf-Coin's contracts. No strategy imports `aiomql` types.

### `geraked/metatrader5`

**Current advertised license:** MIT; verify exact file and commit.

**Study and potentially adapt:**

- MQL5 indicator implementations;
- Expert Advisor structure;
- strategy parameter organization;
- MT5 backtest artifact organization;
- Chandelier Exit, ZLSMA, moving averages, fractals, Bollinger Bands, RSI, MACD, stochastic, ATR stop, SuperTrend, linear regression candles, and related examples.

**Concerns:**

- profitability is not guaranteed;
- some strategies include grid techniques that can magnify risk;
- backtest configuration may be instrument and broker specific;
- indicator availability does not prove strategy quality.

**Native result:** Verified indicator tests and research strategies. Grid behavior is disabled unless an explicit bounded strategy and policy are approved.

### `codedpro/mt5-trade-split-manager`

**Current advertised license:** MIT; verify exact file and commit.

**Study and potentially adapt:**

- REST-to-MT5 bridge patterns;
- TCP request/response flow;
- strict STOP/LIMIT side validation;
- order splitting and volume normalization;
- broker volume-step and digit handling;
- persisted trade-group recovery;
- order reconciliation after broker comment changes;
- safe-shutdown concepts;
- daily loss, position count, and spread checks;
- AI-agent-friendly typed API and MCP boundary.

**Concerns:**

- fixed split ratios are strategy choices, not universal execution truth;
- “risk-free” language after breakeven can ignore gaps, slippage, commission, and broker failure;
- TCP polling and REST architecture must be threat modeled;
- external AI control must remain subordinate to Wolf-Coin authorization and risk.

**Native result:** Configurable position groups, exact broker normalization, recovery, and typed local API. No automatic assumption that split orders improve outcomes.

### OANDA bot repositories

**Study:**

- direct broker REST authentication;
- transaction stream and pricing stream;
- order and position reconciliation;
- account and instrument metadata;
- rate limits and reconnect handling.

**Use:** To design the second forex adapter and prove broker independence after MT5.

### TradingView and PineScript repositories

**Study:**

- signal definition and visualization;
- strategy portability;
- alert/webhook schemas;
- indicator formula cross-checks.

**Policy:** PineScript alerts are untrusted external signals. They become candidate evidence, not direct orders.

---

## 3. Broader trading frameworks

### `freqtrade/freqtrade`

**Study:**

- backtest and dry-run UX;
- strategy registry;
- hyperparameter and report workflow;
- protections;
- trade persistence;
- command and web interfaces.

**License concern:** GPL-family licensing may impose obligations incompatible with some distribution plans. Prefer concept study unless a specific integration decision is reviewed.

**Do not inherit:** Blind parameter optimization or crypto-only assumptions.

### `hummingbot/hummingbot`

**Study:**

- exchange connector architecture;
- market making and arbitrage execution concerns;
- order books;
- connector capability differences;
- gateway and API patterns.

**Use later:** Crypto adapter phase, not the initial MT5 spine.

### `jesse-ai/jesse`

**Study:**

- strategy ergonomics;
- backtest and optimization workflow;
- candles and indicators;
- research-to-live organization.

### `Drakkar-Software/OctoBot`

**Study:**

- visual strategy and bot controls;
- paper and live mode separation;
- exchange integrations;
- model and signal surfaces.

**License concern:** Review GPL obligations before any code adaptation.

### `enarjord/passivbot`

**Study:**

- derivatives exchange behavior;
- high-frequency position management;
- configuration and backtesting;
- exchange-specific precision.

**Reject as default:** Unbounded grid or perpetual-futures risk assumptions.

### `nautechsystems/nautilus_trader`

**Study:**

- event-driven architecture;
- research/live parity;
- high-performance order and portfolio models;
- deterministic simulation and adapters.

**Use:** Architectural comparison before performance-critical redesign. Avoid premature complexity.

### `QuantConnect/Lean`

**Study:**

- multi-asset domain modeling;
- brokerage abstraction;
- corporate actions and complex assets;
- research/live separation;
- portfolio accounting.

**Use later:** Stocks, futures, and options planning.

### `Lumiwealth/lumibot`

**Study:**

- same-strategy backtest, paper, and live flow;
- multi-asset broker interfaces;
- strategy scheduling and lifecycle.

---

## 4. AI and quantitative research sources

### TradingAgents-style systems

**Study:**

- multiple analytical roles;
- bull/bear debate;
- risk and portfolio review;
- final decision synthesis.

**Policy:** Debate increases hypothesis coverage but does not create market truth. All claims must map to Wolf-Coin evidence IDs.

### FinRL and reinforcement-learning repositories

**Study:**

- environment design;
- reward-function pitfalls;
- train/validation/test separation;
- transaction costs;
- baseline comparison.

**Use later:** Research only until stability, interpretability, and risk behavior are proven. RL agents do not enter early live phases.

### Technical-analysis libraries

**Study and dependency candidates:**

- formula correctness;
- performance;
- NaN and warm-up behavior;
- compatibility with replay and live streaming.

Every accepted indicator receives cross-library fixtures and known-value tests.

---

## 5. Source evaluation template

Create one record per evaluated source under `research/sources/<owner>__<repo>/<commit>.md`:

```markdown
# Source evaluation

- Repository:
- Commit:
- Retrieved:
- License:
- Files reviewed:
- Maintainer/activity observations:
- Capability studied:
- Security concerns:
- Trading-risk concerns:
- Test quality:
- Accepted concepts:
- Adapted code and attribution:
- Rejected concepts:
- Native Wolf-Coin destination:
- Required tests:
- Reviewer verdict: ACCEPT | CONDITIONAL | REJECT
```

## 6. Clean-room and attribution rules

- Preserve all required copyright and license notices for adapted code.
- Add source and commit references to `THIRD_PARTY_NOTICES.md`.
- Do not remove author names from copied or modified licensed files.
- When concept study is selected, document the behavior and implement through Wolf-Coin contracts without copying source text line for line.
- Never mix incompatible licensed code into a file without a reviewed distribution decision.
- Do not copy secret files, datasets with unclear rights, compiled binaries, branding, or misleading performance claims.
- Public-source availability does not mean unrestricted reuse.

## 7. Research priority order

1. Sergeant evidence and verdict concepts.
2. OpenClaw scheduling, recovery, fallback, doctor, and gateway concepts.
3. `aiomql` MT5 orchestration and domain separation.
4. `mt5-trade-split-manager` broker normalization, API bridge, and recovery.
5. `geraked/metatrader5` indicator and strategy fixtures.
6. Freqtrade/Jesse/Lumibot backtest and strategy lifecycle comparisons.
7. Hummingbot for later crypto connectors.
8. NautilusTrader and LEAN for long-term architecture stress tests.
9. TradingAgents and FinRL for optional research intelligence.

The first implementation phase should borrow architecture and failure-handling lessons, not chase the most complicated strategy.
