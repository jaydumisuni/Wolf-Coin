# Wolf-Coin — General website observation reasoning (2026-11-24)

**Backend extension**: owner-defined capability is to organize data from any new website without requiring a manual website-specific adapter or a preselected task. The frontend/browser remains independently owned.

## Existing math and new evidence organization

The existing Wolf-Coin source contains quantitative forecasting, probabilities, bookmaker no-vig comparison, proper scores, fee-aware expected value, and simulation/journal components. The missing component was universal observation interpretation, not a fresh model or another PAPER-only constraint.

Native frontend `wolf.browser.v1` observation → `wolf-browser-normalize` (one generic local translator) → signed `wolf-app-bridge` `observation.discover` → `wolf.app.observation-reasoning.v1`.

The normalized observation document `wolf.browser.evidence.v1` includes source hostname, timestamp, session observation, optional account identity, evidence hash, arbitrary label/value pairs, accessible controls and quoted market offers. It does not transmit website credentials, session cookies, raw DOM, screenshot bytes or query-string credentials. The evidence hash is a digest of the **normalized local evidence**, not independent proof of server truth.

The mathematical reasoner uses token-vector cosine similarity and inverse document frequency computed from the current observed page to organize general financial concepts. It returns typed facts with similarity scores, source labels, numeric decimals/currency, relationships, site controls, market offers and conflicts. Unknown concepts remain `UNCLASSIFIED` and are not treated as unsupported sites. Numeric 750 and 750.00 agree; materially different values conflict.

The next task is selected from the data **without the caller supplying a goal**: restore login, wait for connectivity, refresh stale observations, associate a verified account, reconcile financial discrepancies, discover a market/selection, evaluate it with models, synchronize finances, inspect site controls, or organize newly encountered evidence.

For back-bet decimal odds, the market-implied probability is `1 / quote`. This is not a prediction or proven edge. Market quotes are prepared for the established strategy/model mathematics; `forecast_probability` remains null and `edge_verified` false until an actual model forecast is available. Trading prices are never treated as bet odds. No new global financial lock is introduced.

## Frontend handoff

The existing v0.6 native Chromium host emits `wolf.browser.v1` snapshots, DOM inventory and opportunity candidates. The backend provides `wolf-browser-normalize` as a host-side stdin/stdout utility (no provider API and no network listener), converting native observations into the existing signed IPC evidence schema. The Electron source, private D-XQT payload, nine-screen design, mobile code and browser packaging are not modified by this extension.

The current frontend's DOM opportunity extractor still uses a tagged-element path for some quotes; arbitrary image-only or unlabeled pages may require additional structural, visual or learned-language interpretation. The new generic reasoning module supports unknown labels as data but **does not prove general autonomous website operation or profits**.

## Verification scope

Synthetic unknown-site observations prove task discovery, label/value classification, visible text normalization, signed bridge compatibility, numerical conflict detection, market identity discovery, and sensitive-field exclusion. Actual browser effect, money movement and native desktop/Android packaging remain the independent frontend and future joint acceptance work.


## Native Chromium fixture consistency correction

The actual owner's Electron host fixture emits a `wolf.browser.v1` dashboard snapshot and a `wolf.browser.v1` DOM inventory, but the fixture's `domSnapshot` was taken on the **login page before navigation**. Observed Chrome state therefore differed across the two captures even though the browser session and account were real. The universal translator now compares the DOM and snapshot page URL and capture timestamps (within 30 seconds); if they differ it **excludes the stale controls** and annotates `dom_controls_match_current_page=false`. Actual financial page facts are preserved. It also prevents dimensionless odds from inheriting account currency and preserves unknown currency on ambiguous `$`-prefixed amounts. The frontend was not modified.

The first real fixture capture is stored privately at `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/site-neutral-20261124/frontend_fixture_instrumented_copy/captured-browser-observation.json` and is a **local controlled fixture**, not a sportsbook. The only modification to the host test harness was a private, isolated duplicate of `main.cjs` used to print the browser observation; the owner-maintained host source is unchanged. The capture is used as a source for installed-package replay, not committed to source control.


## Source and installed a11 verification (2026-11-24)

- **Frozen implementation source**: `b1034a2a3ffded8d130c169b1f78effdd4936539`; `0.1.0a11` offline wheel SHA-256 `21f395977c51b103b13373211f934242fc8b8875b8170156dae47bd7773207d0`. The wheel contains the generic translator, evidence reasoner and both CLI entrypoints, and installs in a fresh Python venv without NumPy or external provider API.
- **Actual isolated Chromium capture** from the owner's frontend: `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/site-neutral-20261124/frontend_fixture_instrumented_copy/captured-browser-observation.json` SHA-256 `58dd0928520394d87f3b428eb37e527f284f3f69668d2781c6e245bb817ea117`. The owner-maintained frontend source was not changed; an isolated private copy printed the fixture observation for testing. The controlled native Chromium flow passed login, account observations, per-account isolation, logout and persisted-session restoration.
- **Installed signed-native-IPC proof** `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/site-neutral-20261124/installed-a11/installed-site-neutral-proof.json` SHA-256 `d893e0cef6983b8b79a6687270f17dac383259406b5483fb74849bdfd9ee2ba7`. The ORIGINAL captured timestamp was stale, so `observation.discover` correctly recommended `REFRESH_BROWSER_OBSERVATION`. A **synthetically re-timestamped replay** of that same local fixture then selected `EVALUATE_MARKET_WITH_MODELS` without a supplied goal. That replay is **not a fresh browser capture**. Controls from the previous login-page DOM were excluded. An authenticated IPC request whose evidence hash was altered after signing was rejected. The response identified ZMW 750 balance, ZMW 100 pending, ZMW 60 realized P/L and quote 2.10 with dimensionless odds. It correctly left `forecast_probability` null and `edge_verified` false.
- **Source regression**: 437/437 passed, including 28 focused evidence/translation tests. A CLI-subprocess test was made source-root aware to run independently under Cookpit, with **no application-code changes after the wheel implementation freeze**.
- Real bookmaker/broker settlement, predictions for unseen instruments, broad language-model semantics, complete native Wolf Browser application integration, Android packaging and live money remain separate post-integration acceptance. No new research/paper global application restriction was introduced; the existing a6 laboratory service remains unchanged.

## Cookpit independent acceptance (manual, 2026-11-24)

- **Cookpit micro PASS**, 28/28 website-neutral classification/ingress tests plus the source-bound native signed-IPC proof verifier: `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-site-neutral-reasoning/evidence/20261124T041700Z-micro-c884fe8754ca.json`.
- **Cookpit heavy PASS**, 437/437 full Wolf-Coin tests plus isolated offline a11 wheel SHA check, installed new modules/CLI entrypoints, and unchanged active a6 paper laboratory service: `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-site-neutral-reasoning/evidence/20261124T041701Z-heavy-c884fe8754ca.json`.
- The first Cookpit micro verifier could not import the CLI subprocess under its isolated environment. The **manual Cookpit profile**, not application code, was corrected to give its test subprocess an explicit source PYTHONPATH. Those failed attempts remain in local evidence; final micro/heavy receipts independently passed on source review HEAD `fc80684411368d42565628a5ed4f163e57e72fc4`.
- No new scheduled supervisor, production activation, site-specific adapter, browser UI replacement or real-money authorization was created.
