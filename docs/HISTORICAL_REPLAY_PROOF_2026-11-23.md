# Wolf-Coin football odds research — first real strategy falsification

**Scope:** Private historical research only. No real funds, live bookmaker connection, or strategy promotion.
**Input:** Football-Data.co.uk Premier League E0 historical CSV using quoted Bet365 opening 1X2 odds. Data was downloaded once into Wolf-Coin's private KRATOS .workspace; raw CSV files are not committed.

## First experiment (2023/24 train, 2024/25 holdout)

- 2023/24 SHA-256: `b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3`.
- 2024/25 SHA-256: `d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4`.
- Both seasons contain 380 matches. Model was simple Elo teams + trained draw prior, with EV threshold 0.05, one 0.5%-of-virtual-bankroll paper stake per match day maximum, 2% hypothetical winning-profit commission.
- **102 paper selections; 10 wins; K100 -> K78.609474. Net -K21.390526. Return on total staked virtual funds -48.23%.**
- Model Brier score 0.607806 was worse than bookmaker de-vigged probability baseline 0.578664 (lower better).
- **Verdict: NO EDGE ESTABLISHED; DO NOT FUND OR PROMOTE.** Correct code is not the same as profit.

The first result has been inspected and thus 2024/25 is **validation data for subsequent model exploration**, not a new untouched holdout.

## Predeclared second experiment — frozen BEFORE seeing 2025/26 outcomes

- Training 2023/24. Validation 2024/25. Reserve 2025/26 as fresh final evaluation. The final dataset has **not been downloaded** at this freeze point.
- Candidate weights predeclared: 0.0, 0.2, 0.4, 0.6, 1.0, combining Elo and bookmaker de-vigged probabilities.
- Select by validation proper scoring (Brier) alone, not by ROI. Must beat market Brier by at least 0.005 or **ABSTAIN**.
- One daily maximum paper selection, no odds above 5.0, EV above 0.05, maximum stake 0.5% of current virtual bankroll, K0.01 stake increment, 2% hypothetical winning-profit commission.
- Validation scores: market 0.578664; blends 0.2: 0.581697, 0.4: 0.586128, 0.6: 0.591957, 1.0: 0.607806. No candidate improves market sufficiently, therefore **selected candidate = NONE**.
- The three-window runner must evaluate and report final calibration with no bets if the validation decision stays unchanged.
- A final positive paper result would not establish real provider access, actual executable prices, stable profitability or live capital readiness. This experiment cannot promote a strategy.

## Executable tool

Commands provided after installation:
- `wolf-lab --train PATH --holdout PATH --train-sha256 SHA --holdout-sha256 SHA --report-json PRIVATE_OUTPUT --report-html PRIVATE_OUTPUT`.
- `wolf-lab-walkforward --train PATH --validation PATH --final PATH --train-sha256 SHA --validation-sha256 SHA --final-sha256 SHA --report-json PRIVATE_OUTPUT --report-html PRIVATE_OUTPUT`.

Both commands are offline; outputs are static HTML + JSON, private and immutable on rerun, with SHA-256 input binding and chronological refusal checks.

**Limits:** Football-Data historical opening prices are not proven obtainable at a sportsbook available in Zambia, and pre-kickoff timestamps are not established per quote. First backtest is hypothetical research, not actual bets. Data are not redistributed in the public Wolf-Coin source. No real-money interface added.


## New final window — run after source freeze

The source and fixed three-window selection law were frozen at commit `738f81922c66dc4707445835ca467c68e8f072aa` before retrieving 2025/26.

- Final 2025/26 independent input SHA-256: `3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62`; 380 matches, 15 August 2025 through 24 May 2026.
- The validation period did **not** admit any model, so the frozen final protocol issued **0 bets** across 114 historical match days. Virtual K100 remained K100, net K0.
- Final bookmaker no-vig Brier score: **0.611512**. With no model admitted, candidate Brier is the market baseline at **0.611512**.
- **Finding: strategy evidence is INSUFFICIENT; NO PROFIT SIGNAL OR REAL-MONEY RELEASE.** A zero-loss abstention is not a profitable strategy.
- First real historical ELO trial remains a recorded **-K21.39** virtual loss; do not erase or reframe that failure.
- Reports are retained privately on KRATOS:
  - `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/odds-replay-20261123/epl-odds-holdout.json`
  - `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/odds-replay-20261123/epl-three-window-2025-26.json`

## Operator UI

The read-only, loopback-only `/lab` dashboard displays the two candidate results. It reads only the two explicit report files configured at service startup and does not expose historical source CSVs, credentials or execution endpoints. The navigation includes Sports / Trading / Strategy Lab / Funding readiness. No optimization against the final season is permitted for this frozen model generation.

The laboratory's future purpose is to evaluate genuinely different data features and model families using new training/validation partitions and a **new untouched evaluation period**. Neither favorable code tests nor historic odds by themselves qualify automated betting.
