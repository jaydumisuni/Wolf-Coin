# Wolf-Coin — funding and provider qualification, 2026-11-23

**Classification:** PUBLIC-SAFE ENGINEERING AUDIT / NO REAL FUNDS AUTHORIZED
**Reviewed:** 2026-11-23 (Africa/Lusaka).
**Source generation:** existing P0–P12 and WX-0…WX-10 contracts, branch `work/wx-tenfold-cookpit-20261123`.

## Real-money admission: external dependencies

Neither sport betting nor trading is ready for funds. No confirmed sportsbook or broker was selected or KYC-proven, no provider account or permitted live API is connected, there is no broker DEMO submission/restart proof, and the historical market data does not establish a predictive betting edge.

Wolf-Coin must never self-authorize by constructing a local `ProviderReview` object, storing an offline statement, or setting a flag. A legally/contractually qualified interface, owner sign-off, independent risk/execution review and actual reconciled account state are mandatory. The two financial domains require **separate** release decisions.

The new `wolf-funding-readiness` CLI reports current missing conditions. It always returns `funding_permitted=false`, `max_customer_deposit_authorized_ZMW=0`, no transfer adapters and no online credential use. An operator-supplied name is informational only.

## Public provider screen (research leads, not selected partners)

| Candidate | Verified public information | Result |
|---|---|---|
| GSB Zambia sportsbook | GSB `Terms and Conditions` clauses 17.2.20 and 17.2.23 prohibit automated scraping and third-party AI/bot assistance tools. | **Not eligible for Wolf-Coin automated betting** under these terms; no bypass |
| betPawa Zambia | Local operator identifies its licensed Zambian entity, but public-facing account ownership alone does not establish a third-party automated execution API or license. | **UNVERIFIED**; no asserted automation rights |
| Betfair Exchange API | Betfair advertises a licensed Exchange API, but explicitly says the Exchange API cannot place Sportsbook bets. A KYC-verified account and relevant application key are required for the Exchange API, and Zambia account/API eligibility remains unconfirmed. | **UNVERIFIED** for Zambia, **not** a Sportsbook API |
| OANDA Global Markets, trading | OANDA publishes an MT5 demo/live account workflow, including demo server, and its investor password can support read-only access. OANDA v20 REST documentation specifically excludes Global Markets accounts. | MT5 **research candidate only**, requires customer onboarding, demo account and qualified Windows host |
| MetaQuotes / Windows MT5 | Windows ATHENA was reachable 2026-11-23; read-only process/software inventory showed no running `terminal64.exe` or installed `MetaTrader5` Python module. | **NOT INSTALLED / NOT QUALIFIED** |

Official sources:
- https://help.gsb.co.zm/terms-and-conditions/
- https://www.betpawa.co.zm/About
- https://support.developer.betfair.com/hc/en-us/articles/115003886731-Can-I-place-Sportsbook-bets-via-the-API
- https://support.developer.betfair.com/hc/en-us/articles/360002464152-Which-API-Licence-Do-I-Require
- https://support.developer.betfair.com/hc/en-us/articles/28271961503516-Which-IP-regions-are-restricted-from-accessing-the-Betfair-API
- https://developer.oanda.com/rest-live-v20/introduction/
- https://help.oanda.com/bvi/en/faqs/mt5-user-guide-bvi.htm

No account-access tests were made against these operators, and their eligibility may change.

## Zambia funding and cost treatment

Betting Levy Act, 2025 (Act 27 of 2025) specifies a **5% betting levy paid by the betting company** on the covered deposit/withdrawal activity. This does not itself establish a 5% deduction from the player's credited funds; actual provider, payment and wallet receipts determine customer costs.

Source: https://zambialii.org/akn/zm/act/2025/27/eng%402025-12-30 and https://www.parliament.gov.zm/node/12777

The funding model has no payment API, no deposit action, no top-up action and no live ledger state. It requires explicit account identity, independent external-wallet and provider-account statement references, documented customer fee and exact Decimal conservation. Separate ZMW/USD FX reconciliation requires a fresh rate, explicit source-side fee and a verified target credit. All results are **rehearsal only**, including when locally asserted evidence flags are true. Foreign-currency deposits are not permitted by the real-money system.

## Historical strategy baseline: reproducible, not profitable

Source: **openfootball/football.json** CC0/public-domain data, two fixed Premier League JSON files retrieved directly from the upstream repository, for private project research; not published as raw data in Wolf-Coin.

- 2024–25 train: 380 match results; SHA-256 `c3d18f552d83382cd4b6b21127adbbfe38e7f8618ddc979fb5404f2df07d0a75`.
- 2025–26 holdout: 380 match results; SHA-256 `d6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1`.
- Candidate Laplace-smoothed frequency-only baseline: **Brier 0.65674461**, log loss **1.08466885** on holdout.
- Uniform 1X2 baseline: **Brier 0.66666667**, log loss **1.09861229**.
- These data have **no executable bookmaker odds** or verified customer stake costs. Small improvement over a uniform research baseline is not a profitable-edge claim.

Sources: https://github.com/openfootball/football.json ; https://github.com/openfootball/football.json/blob/master/LICENSE.md

The official Football-Data.co.uk website has a separate, restrictive fair-use policy: personal or academic research only, at most light automated downloads, and no commercial/AI-training right by default. No football-data.co.uk CSV files were downloaded or used in this Wolf-Coin research run. See https://football-data.co.uk/contact.php.

## K100-equivalent rehearsal rule

The default public test policy has an illustrative **100 ZMW per-domain maximum**, with separate wallets and no automatic transfer, and bounded modeled action risk of **0.50 ZMW (sports)** or **0.25 ZMW (trading)**. A sportsbook minimum stake over 0.50 ZMW or a broker minimum loss above 0.25 ZMW causes abstention rather than risk expansion. The sample numbers are software research defaults, not instructions to deposit.

Actual risk minimums, currencies, bank/mobile-money funding methods, FX rates, fees, operator restrictions and customer limits are **unverified** until sourced from a real approved provider account. The user must not fund based on a simulated capability check.

## Installation / evidence

- `wolf_funding.reconcile`: two-source offline funding statement arithmetic, scoped plans, replay and no automatic funds.
- `wolf_funding.fx`: strict two-currency rate/fee/credit rehearsal.
- `wolf_funding.provider`: fail-closed compliance/capability screening (permissions, identity, min stake, currency, fees, suspended account).
- `wolf_funding.cli`: read-only funding readiness output; cannot ever authorize a transfer.
- `wolf_lab.backtest`: bounded source-hash intake, chronological holdout enforcement, Brier/log-loss/uniform baseline.
- These are **source candidates** until independently reviewed and installed into a properly pinned release. The active KRATOS `wolf-coin-paper-preview.service` is separate, read-only and unchanged.

## Remaining before independent funding acceptance

1. Sports: select a Zambian-eligible, licensed operator with explicitly permitted Wolf-Coin execution, or constrain sports to manual placement while Wolf-Coin remains research-only.
2. Trading: select and verify the exact broker/division and permissible execution route. For MT5, set up a true demo on the Windows workstation; prove account identity, provider-side stops, spread/lot constraints and restart reconciliation.
3. Verify KYC, source/data rights, actual fees, funding rail, FX conversion, practical minimum exposure and account statements.
4. Execute sustained out-of-sample research/paper/shadow with real permitted quotes and a strategy that clears costs and independent review. A train/holdout score alone is insufficient.
5. Finish the full Tenfold/Cookpit gate review and owner-signed activation decision for **each** domain. Never promote automatically.

**Current admission result: REAL_FUNDS_NOT_AUTHORIZED. No deposit or execution has been initiated.**


## Paper console presentation

The read-only browser console adds `/funding` and `/api/funding-readiness` to existing `/sports` and `/trading` pages. All pages are loopback-only, and POST is rejected. It displays both default ZMW budgets, the *zero* approved customer deposit, and the external blockers. Neither endpoint can choose a provider, sign an approval, read credentials or move funds.

**Current isolated-source suite:** 187 passing tests (including the funding dashboard). This is a preparation milestone, not permission to move money. Final installed-source identity and Cookpit receipts must be pinned separately after commit.
