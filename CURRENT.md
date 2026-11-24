# Wolf-Coin — CURRENT

## Native browser evidence → site-neutral reasoning candidate (2026-11-24)

- New isolated backend `0.1.0a11` consumes the existing frontend's `wolf.browser.v1` via **one generic `wolf-browser-normalize` translator** and signed native IPC `observation.discover`. It applies current-page token-vector/IDF semantic similarity and numerical normalization, preserves new and unrecognized site facts, selects the next task without a preselected goal, and exposes market-implied probabilities when supported. **No site allowlist, bookmaker API, global application mode lock, or frontend modification.**
- A native Chromium/Electron v0.6/0.7-dev fixture on KRATOS passed login, balance/pending/P&L capture (ZMW 750/100/60), isolated account sessions, restart/login persistence and logout. Actual native snapshot and DOM were captured separately in private proof. That capture revealed the DOM inventory came from an older login page; backend now rejects stale-page controls rather than attaching them to the authenticated dashboard. Odds remain dimensionless; ambiguous currency symbols are not relabeled as account funds.
- Synthetic tests validated real browser contract normalization, unknown text values, account recovery, conflicts, no false edge/profit claims and fresh evidence task selection. The browser host and strategy/forecast model wiring remain independently owned/qualified; the reasoner is deterministic semantic math, **not an already trained general website agent**. See `docs/OBSERVATION_DRIVEN_INTELLIGENCE_2026-11-24.md`.
- **Implementation `b1034a2`**, wheel `0.1.0a11` SHA-256 `21f395977c51b103b13373211f934242fc8b8875b8170156dae47bd7773207d0`, installed signed-IPC proof SHA-256 `d893e0cef6983b8b79a6687270f17dac383259406b5483fb74849bdfd9ee2ba7`; **437/437 tests passed**, including 28 focused. The real original Chromium fixture was stale, while a marked synthetic currentness replay selected market evaluation without a goal. Details in the handoff; Cookpit independent acceptance is recorded in its local manual evidence.

---

## Owner-directed removal of app PAPER/research fallback (2026-11-24)

- **The old application default `RESEARCH_ONLY` restriction was not user-approved and is removed** in the isolated `0.1.0a10` backend. Financial actions remain context-selectable: `PLACE_BET`, `CANCEL_BET`, `PLACE_TRADE` and `CLOSE_POSITION`. Intelligence research/learning is available as a separate task, not a restrictive app operating mode.
- The unconditional `live_enabled=false`/`financial_execution_authorized=false` response keys were removed; the response protocol is now `wolf.app.bridge.v2`, request still `wolf.app.request.v1`. The `--research-unkeyed` product CLI flag is removed. Native browser workflow selection and actual platform outcome receipts remain distinct: only the host/browser can execute and verify an actual order.
- Existing v1 app DBs migrate to schema 2, archiving old status labels as `ANALYSIS_ARCHIVED` with audit preservation, including cached idempotent outputs. Historical paper simulator and trained research source are retained as development evidence, **not a product mode**. KRATOS paper lab service and user frontend remain untouched.
- Source implementation `b29288f`, a10 offline wheel SHA-256 `a2974856bf5c325183acb8e447d0405c49b8bef6c03db04abb923711ebf6f9cf`, **409/409 PASS**, Cookpit micro/heavy PASS, installed signed IPC proof SHA-256 `202cc5c3d1b8941ac5df09a33b958ecfc583eb8cc769940c20d782b36338117b`. No real website or money action has been performed.
- See `docs/WOLF_APPLICATION_BACKEND_HANDOFF_2026-11-23.md` for current a10 interface; older a8/a9 notes are historical, not current restrictions.

---

## Context-aware capability routing correction — 2026-11-24

- Wolf-Coin **must select what capability to use, when and on which site/account**; it is not a research-only trading bot. The a8 `RESEARCH_ONLY`-only decision path was overly narrow, not an approved product restriction. Isolated a9 candidate implements signed IPC `context.route` for learning, research, browser interaction, financial sync, trading/betting and position exits.
- The router chooses `READY`, `DISCOVER` or `RECOVER` based on actual task, account/domain, authenticated session, freshness/conflicts, site affordance and scoped permissions. **No global capability lock was added.** Context-ready financial `decision.propose` persists `BROWSER_HANDOFF_READY`; a native submission receipt remains awaiting platform reconciliation.
- Source implementation `40e5937` and offline wheel a9 SHA-256 `3fdb152d158b5837c2d01390531a244c3f275bd19dde074d326661d4bc0e2438` pass **404/404 tests**; Cookpit micro/heavy PASS, with an installed signed-IPC proof SHA `77e6151ea4dff2bbdc45c06ba815907b8b6ddde3c54d16dc647d05349e62357f`. No new lock or money/website execution was introduced.
- This is deterministic action selection/handoff, not a trained general browser model, a connected Chromium/WebView host, a real order or proof of profitability. Frontend/browser/installer implementation remains with its owner; paper model and active service unchanged. See `docs/WOLF_APPLICATION_BACKEND_HANDOFF_2026-11-23.md` and `contracts/wolf-app-bridge-v1.schema.json`.

---

## New isolated application-backend integration candidate (2026-11-23)

- A separate versioned backend `0.1.0a8` now provides source-owned `wolf_app`, **no browser, UI or app-packaging replacement**. It implements native host signed JSON-line IPC, account registration/removal, session state and startup revalidation, evidence-hashed financial snapshots and transactions, cross-source conflict detection, currency-separated financial overview, paged history, audit chain, explicit read-only sync planning and durable browser observation jobs with UNKNOWN reconciliation. Decision proposals are RESEARCH_ONLY; no orders, funds or API dependencies.
- Native host backup/restore uses consistent SQLite copies, private create-only paths and post-restore session revalidation. Browser credentials never enter this backend; native host still owns secure Chromium/WebView profiles, keys, OS app lock and encrypted backup.
- Backend implementation and full protocol handed off through `docs/WOLF_APPLICATION_BACKEND_HANDOFF_2026-11-23.md` and `contracts/wolf-app-bridge-v1.schema.json`. Source and host tests **378/378 PASS**, focused account/backend tests **49/49 PASS**, Cookpit manual micro/heavy PASS against implementation `0cfcc67`. The `0.1.0a8` offline wheel SHA-256 is `c4d0be16ed9a69806e4fcf47cdfec0d06e50e8f7efb2e41205cebc48aa537a91`, with a validated signed cross-process and backup/restore receipt; full details in the handoff document.
- Active KRATOS `wolf-coin-paper-preview.service` remains stable a6; no app frontend or Wolf Browser integration has happened yet. Final real platform login, integration, authenticated DOM/network observations, Windows/Linux/Android app acceptance, production model/gate admission and live financial decisions remain separate.
- **User-approved work division preserved:** frontend/browser/packaging belong to frontend owner; intelligence, finance and backend bridge belong here.

---

## Latest cross-project gate research (2026-11-23)

- **Installed runtime remains a6**: KRATOS native PAPER-only `0.1.0a6` at `http://127.0.0.1:18766/gates`. Separate offline **installed and Cookpit-verified research package** `0.1.0a7` adds a match-day uncertainty analyzer; do not confuse candidate source with installed PAPER service.
- Private SUP draft [PR #1](https://github.com/jaydumisuni/SUP/pull/1) adds a non-executing product-owned typed candidate intake (120 source tests PASS); `TYPED_CANDIDATE_INTAKE_REVIEW_ONLY`, not an independently admitted SUP/Formula method. Installed SUP unchanged.
- The fabricated-odds K5.61 hypothetical gain has a **5,000-replicate, 17-day clustered 95% interval of −K2.5655 to +K13.6205** on 36 selections; zero included. Neither market profitability nor fresh unseen test proven.
- Provider research identifies an official FP Markets Zambia MT5 demo/EA candidate requiring actual account-holder onboarding; Smarkets API has a £250 setup fee and location uncertainty; broad OANDA country navigation differs from division-specific eligibility. No provider account or venue permission proven.
- Candidate `0.1.0a7` wheel SHA-256 `25c7f1be66cb58d05e95f1ac7434fb2875d329e06eec9ae8725c50e7886dbeeb`. Manual Cookpit micro 6/6 and heavy Wolf 329/329 + SUP 120/120 PASS; source implementation `02f3a9eaba61ff233df94d8188127a16f229dcfc`. Native PAPER-only a6 unchanged.
- Both domain release inventories remain **0/5 externally accepted**. Exact proof and dependencies in `docs/FIVE_DELIVERY_GATES_2026-11-23.md` and `docs/FUNDING_AND_PROVIDER_DILIGENCE_2026-11-23.md`. No funding or live execution.

---

## Current installed gate-evidence release — 2026-11-23

**KRATOS Wolf-Coin `0.1.0a6` is running PAPER-only, with a new read-only Five gates page `http://127.0.0.1:18766/gates`. All five real-world release gates remain unaccepted.**

- New source `45b2e3345cb465082614fcf25807b6e7db3faf40` adds strict pinned offline 1X2 quote source/UTC/kickoff checks, prior-result-separated fee-aware shadow audit, and idempotent synthetic-only scheduling based on the existing durable paper journal. No broker/sportsbook client, external API or funding transfer was added.
- The source-bound 45-match **invented odds** rehearsal generated 36 hypothetical selections and **K5.61 counterfactual modeled gain**. That amount is NOT real or validated profit, and the model has no proven bookmaker edge.
- New domain-separated five-gate `wolf-five-gates` CLI reads Tenfold without mutating authority. Sports **0/5**, trading **0/5** accepted. Tenfold campaign sports 0/24 proven; trading 0/13. SUP still `NO_VIABLE_NEURAL_ROUTE`; Formula typed method candidate not independently signed.
- Wheel SHA, original user-service rollback, paper ledger preservation, negative HTTP tests and exact source receipts: `docs/FIVE_DELIVERY_GATES_2026-11-23.md`. Cookpit manual micro **40/40 PASS**, heavy **323/323 PASS** + **9/9 existing Formula native tests**. Native service enabled and loopback `127.0.0.1:18766` only, `POST /gates` 405.
- **Still required:** independently qualified Formula/SUP method; executable licensed time-bound data; demonstrated profitable unseen strategies after real costs; authorized broker/bookmaker demo, settlement/halts; owner-signed per-domain production review and Tenfold approvals. No money pilot admission.

---

## Active verified release / typed research frontier (2026-11-23)

**PAPER-only Wolf-Coin `0.1.0a5` is installed and enabled on KRATOS, with typed tabular CPU research candidate verification; no positive-EV proof or funding authority.**

- Runtime wheel `0.1.0a5`, source `5219fccf13c210ac8308c1bda62bb49bbbf302a9`, loopback `127.0.0.1:18766`; read-only Neural view `http://127.0.0.1:18766/neural`. Existing paper balances and previous release unit preserved.
- The `wolf-tabular` research CLI reproduces the frozen CC0-only 2,660-training/380-validation MLP weights exactly and replays 45 already-inspected predictions with an **independent standard-library numerical checker in a minimal environment without NumPy**. Maximum probability error `7.732e-13`. It is a **Wolf-Coin-owned research adapter**, NOT a SUP/Soup admitted method or Formula mathematical certificate.
- Existing Formula P13 Director/SUP boundaries verified with 9/9 native Rust tests; the Formula review manifest is candidate-only and not signed. SUP G5 stage remains `NO_VIABLE_NEURAL_ROUTE` (0/10 borrowed Soup methods qualified for this tabular model).
- Cookpit micro/heavy **PASS** on corrected test HEAD `ba3dc4971b92dedf96b3d3531ac6e373685c48ce`: 35 focused and 283 complete tests, native host and Formula advisory checks. The earlier failed micro receipt and exact `PYTHONPATH` regression correction remain recorded.
- Review receipt, SHA hashes, no-money bounds, and rollback: `docs/CC0_NEURAL_POSTFREEZE_PROOF_2026-11-23.md`. Next independent engineering authority: implement and review a genuinely compatible typed SUP/Formula admission route **without inventing Soup/SUP-Bit support**, then gather a larger untouched evaluation and licensed executable odds before even considering funding.

---

## Authoritative latest status — 2026-11-23

**Patrol registration RESOLVED; native KRATOS paper preview INSTALLED and RUNNING. Live financial execution remains LOCKED.**

- Canonical Patrol project: `/home/kratos/projects/Wolf-Coin`, owner kratos, `0700`, registry and Git route verified.
- Autonomous registration path restored in active Patrol main at `257f78dbf75c20576d6fa7d9d30aa111372fc2ed`: hardened Oracle terminal uses preexisting privileged Oracle helper; ordinary sessions retain noninteractive sudo. Tested 45/45. User input is **not** required for subsequent properly authorized project registrations.
- Protected Wolf-Coin main unchanged; active construction worktree at `.workspace/worktrees/wx-first-light-20261123` from `f2fe764cfd69676b5d521d3d823afb6d86133d07`.
- Source and package: 31/31 tests passed on KRATOS. Installed offline wheel SHA-256 `a99589dcd248424c45e04e6c85171cb22aa38f6663c233d40802d9c973a3ad46`.
- User service `wolf-coin-paper-preview.service` is active, enabled and loopback-only on `127.0.0.1:18766`. Sports `/sports` and trading `/trading` tested. Two separate **virtual** K100 balances; no real deposits, provider or execution adapters.
- Cookpit manual-only source and native-host micro/heavy: PASS. Tenfold 24-node durable campaign P0: **READY, NOT PROVEN**; 0/24 gates earned; no new GPT supervisor.
- See `docs/KRATOS_PAPER_HOST_PROOF_2026-11-23.md` for source digests, installed runtime, negative HTTP controls, Patrol evidence, Cookpit receipt location and recovery. Real-time market data, autonomous decision loops, predictive edge and live sportsbook/broker interfaces remain incomplete.

**Next engineering frontier:** P0 source/architecture acceptance and deterministic scheduler/execution state machine, with independent gate evidence. Do not conflate a working paper dashboard with finished Wolf-Coin or live financial authorization.

---

## Typed tabular CPU research candidate for Formula review — 2026-11-23

- The exact Formula P13 and SUP/Soup borrowings were inspected; none supplied an existing qualified tabular 1X2 trainer. **No change** to SUP's `NO_VIABLE_NEURAL_ROUTE` or Formula mathematical authority.
- New Wolf-Coin-owned `wolf-tabular` research CLI has `retrain-proof`, `build`, and independent `verify` operations. Full 2,660-fixture CC0 training and 380-fixture validation regenerate exactly the frozen MLP weights/selection. An independent **stdlib-only** numerical verifier checks the 45 already-examined predictions within `3e-12`.
- The adapter is tightly bound to pre-2026/27 frozen model/source hashes, excludes non-CC0 learning sources, uses no live sportsbook account and contains aggressive corruption and forged-authority refusal tests. It is **candidate-only** for Formula/SUP review and does not create a qualifying Soup method or prove financial return.
- Technical detail and qualification limits: `docs/CC0_NEURAL_POSTFREEZE_PROOF_2026-11-23.md`. The currently installed safe paper service remains unaffected by the research adapter.

## SUP capability snapshot completed — 2026-11-23

- Existing SUP G5 Director processed frozen Cookpit, Formula, Simulation, Sergeant and Soup capability evidence for Wolf-Coin. The missing `SUP_SIM` input is complete.
- Director advanced from `AWAIT_CAPABILITY_SNAPSHOT` to **`NO_VIABLE_NEURAL_ROUTE`**. Of 10 considered methods, eight have no verified hardware/task fit and two are donor-unsupported. Next: Full Formula/target-product Director to engineer a compatible tabular route; NO SUP training or financial deployment authority.
- Active checked-out owner HEADs differ from frozen SUP pins. This is contract-pin currentness only, not independent production signatures.
- Repeatable checker `scripts/sup_capability_snapshot.py` and tests `tests/test_sup_snapshot.py`, evidence in `docs/CC0_NEURAL_POSTFREEZE_PROOF_2026-11-23.md`.
- KRATOS PAPER-only `/neural` view shows new status from an immutable private JSON summary. Existing `0.1.0a4` wheel and ledger unchanged; prior user service unit preserved.

## Latest installed CC0 neural proof (2026-11-23)

- Wolf-Coin **0.1.0a4** native research console now active on KRATOS at `http://127.0.0.1:18766/neural`, pinned to `f5e7acac87db6e30d7bd4fa928eb7036cf5c1680`; the earlier resident release and unit remain available for rollback.
- Source-bound **CC0-only NumPy MLP**, frozen *before* 2026/27 outcome retrieval at `170a555`. It scored Brier `0.611911853` vs class-prior `0.657353561` on just **45 scored matches**. 95% match-day bootstrap Brier advantage CI crosses zero, so **no statistically robust edge or profit proof**.
- SUP G5 Director is `AWAIT_CAPABILITY_SNAPSHOT` with exact machine-verified CC0 source receipt; no separately signed approval, SUP training lease, SUP-Bit neural proof or release authority.
- Separate installed research package replayed exact frozen results; **251/251 tests**, Cookpit manual micro/heavy **PASS** against exact installed source; all seven loopback routes healthy, financial POST refused and ledger unchanged.
- See `docs/CC0_NEURAL_POSTFREEZE_PROOF_2026-11-23.md` and immutable private receipts. Do **not** fund, arm live providers, or train on the historical bookmaker CSV.

## New CC0 neural source research — 2026-11-23

- After proving the publisher's limited-use rule, neural training now uses **only OpenFootball CC0 match results** from pinned upstream commit `e6744429`; no Football-Data bookmaker prices entered MLP training.
- The neural architecture/selection was frozen at Wolf-Coin `170a555` before the first retrieval of 2026/27. Training 2,660; validation 380; 2026/27 snapshot had **45 completed of 380 scheduled** matches, latest through September 20. Source 2025/26 has only 353 scored of 380.
- MLP scored **0.611911853** Brier vs historical class prior **0.657353561**, but day-cluster bootstrap confidence interval of advantage **[-0.050237688, +0.158399450] includes zero**. It has NOT established market-relative superiority or profit.
- Separate source audit: 760 historical fixture scores matched a second private source with zero conflicts, no restricted data used in neural training.
- SUP G5 Director accepted a machine CC0 research-only source receipt and advanced to **AWAIT_CAPABILITY_SNAPSHOT**, no training, deployment or funding authority. SUP-Bit did not train the MLP.
- The new native evidence view is `/neural` (installed release qualification follows). Source and proof `docs/CC0_NEURAL_POSTFREEZE_PROOF_2026-11-23.md`.

## Current installed forecast research tool — 2026-11-23

- Wolf-Coin **0.1.0a3** installed on KRATOS at source `7b56d694cade3ee70524a00a495a570d0b3f8faf`. Read-only Forecast CPU page at `http://127.0.0.1:18766/forecast`, alongside original Sports, Trading and Strategy Lab.
- Actual SUP Director G5 returned **AWAIT_SOURCE_QUALIFICATION** for the hashed 1,520-row source candidate; no training executed or authority granted.
- Real validation: bookmaker Brier **0.578663803** versus best CPU candidate **0.580325109**, so **no model admitted or profit proved**.
- SUP-Bit v14 delivered read-only KRATOS resource-fit estimate only; original 0.39-second CPU job measured peak ~41,148 KiB. No football neural model trained or compression performed.
- Exact installed CPU research CLI reproduced corpus/reports; Cookpit manual micro and heavy **PASS** (227 tests) at installed source. No GPT supervisor or real-money execution.
- Evidence/rollback details: `docs/SUP_FORECAST_INTAKE_PROOF_2026-11-23.md`. Remain blocked on independent source timing/rights qualification, then actual neural method and fresh untouched test.

## Latest SUP forecasting evidence — 2026-11-23

- Real SUP G5 Director `sup director` received Wolf-Coin's hashed football learning candidate; stage `AWAIT_SOURCE_QUALIFICATION`, not training. Exact source-bound corpus has 1,520 matches; private train/validation/previously-examined diagnostic groups.
- CPU market-offset model was trained reproducibly on 760 historical fixtures, but best 2024/25 validation Brier `0.580325109` was **worse** than market `0.578663803`. **No model admitted, no profit proven**.
- SUP-Bit v14 read-only resource planner found a declared small CPU workload to `FIT`; it has **not** trained or validated a football neural model. No private SUP-Bit source was copied into public Wolf-Coin.
- `wolf-lab-cpu` and the read-only Forecast CPU browser view are source-implemented. See `docs/SUP_FORECAST_INTAKE_PROOF_2026-11-23.md` for dataset hashes, Director disposition, actual CPU run, resource proof and required independent review.

## Current installed strategy lab (2026-11-23)

- **Wolf-Coin 0.1.0a2 now runs on KRATOS**, installed from source `74ecbd8`, with read-only Strategy Lab at `http://127.0.0.1:18766/lab`, alongside Sports and Trading. The source is pinned in the native user-service configuration and the prior release/unit are preserved for rollback.
- The first real-data 2024/25 replay lost **K21.39 virtual** on 102 historical selections. The frozen three-window validation rejected all candidates; the separate 2025/26 final season issued **zero bets**, so K100 virtual remained K100. **Neither run proves making money.**
- The exact installed CLI reproduced both reports. 213 KRATOS tests passed; Cookpit manual micro/heavy **PASS** at exact source `74ecbd8`. Tenfold has not promoted a money release. No live adapters or funding enabled.
- Full file SHA, provenance, native UI and failure evidence: `docs/HISTORICAL_REPLAY_PROOF_2026-11-23.md`. Next work is genuinely improved forecasting, independent out-of-sample profitability and licensed provider/demo access—not making the risk threshold looser to force bets.

## Latest research lab evidence (2026-11-23)

- Two real Premier League seasons with recorded historical opening odds produced a first ELO strategy failure: **102 hypothetical bets; K100 virtual balance fell to K78.61** (net **-K21.39**). Prediction accuracy also trailed the bookmaker market baseline.
- Historical replay source and three-window candidate-selection rule were frozen at `738f819` before inspecting the separate 2025/26 final season. Validation rejected all predictive candidates; final test made **0 bets** (K100 unchanged), which is capital preservation, NOT profit.
- A native `wolf-lab` / `wolf-lab-walkforward` CLI and read-only `/lab` dashboard are now implemented and tested. No strategy is promoted; no customer money is connected. See `docs/HISTORICAL_REPLAY_PROOF_2026-11-23.md`.

## Latest construction work — paper execution and real-money admission review

- A new isolated feature worktree implements a stricter paper-only execution journal, risk/account preflight, read-only Tenfold pilot gate report and mock-tested MT5 demo inspection. The existing installed paper console is unchanged.
- Source tests: **92 passed** on KRATOS Python 3.14.4, including a physical Linux kill/restart at an in-flight simulation point. No live adapter or real provider account was touched.
- Read `docs/GUARDED_EXECUTION_FOUNDATION_2026-11-23.md` for boundaries and proof obligations. Tenfold P0 remains READY, not PROVEN. The pilot readiness evaluator reports 0 proven trading/sports live gates. No real-money release is authorized.

## Funding admission and licensed research work (2026-11-23)

- Added offline funding/FX reconciliation, scoped provider permission/risk checks, read-only funding gate CLI and a new read-only `/funding` paper dashboard route. No real-money transfer actions or credentials. Source suite: **187 passing** on KRATOS before release packaging review.
- CC0 OpenFootball holdout: 380 train fixtures (2024–25), 380 holdout fixtures (2025–26); baseline Brier 0.65674461 vs uniform 0.66666667, **not positive-EV or actionable bookmaker proof**.
- ATHENA reachable, but no running MT5 terminal or installed MT5 Python module. No sportsbook account/API or broker onboarding verified. Both pilot funding paths remain BLOCKED.
- See `docs/FUNDING_AND_PROVIDER_DILIGENCE_2026-11-23.md`. Keep the running paper preview unchanged and never fund solely because tests pass.

## Paper funding-preview upgrade — installed (2026-11-23)

- New versioned paper release `wolf-coin-core 0.1.0a1` pinned to source `b01d2691f023366fcfc64bfa819beeac72746161`, wheel SHA-256 `f8b360c7266b974692bd33cbab33480642cc3da57758e39d2f4ae7b99f8c5340`.
- Existing KRATOS user service replaced with verified release; rollback unit and previous wheel retained, unchanged virtual balances. GET `/sports`, `/trading`, `/funding`, `/api/funding-readiness` all HTTP 200; POST fails HTTP 405, loopback-only.
- Brave opened the three local views. `wolf-funding-readiness` reports **K0 approved deposits**, no provider connection, no transfer adapter, and independently unearned live release for either domain.
- Tests: **187/187 pass** on KRATOS. No live funds, auto topups, new GPT supervisors or privileged executable links.
- Detailed proof: `docs/KRATOS_FUNDING_PAPER_UPGRADE_2026-11-23.md`. Requalify actual provider/operator identity, data rights, settlement/reconciliation, minimum size and strategy before any real-money pilot. Tenfold still zero PROVEN live-release gates.

## Earlier 2026-11-23 engineering chronology (historical; superseded wherever contradicted by the latest status)


**Assessment:** 2026-11-23. **Status:** planning and source-workforce preparation; no production implementation or live admission established.

### Recovered authoritative baseline

Existing original roadmap is P0–P12 with research and paper mode default, hard risk rules and independent guarded-live admission. The additive docs/WX_MULTI_DOMAIN_ROADMAP.md proposes WX-0–WX-10 without renumbering P0–P12.

A real TTG-Simulation Gen1 runner on KRATOS compared 5 architecture candidates over 40 declared design controls. Original draft: 35/40. Revised five-correction design: 40/40. This is an internally scored structural candidate only, not runtime proof or a success probability.

A real qualified Tenfold Gen1 campaign deriver on KRATOS created a 24-gate blueprint/campaign, with independent derivation PASS and no invented/unmapped obligations. Blueprint digest 2f40206bbfd061b9d14adafea7eadfb942b6a217a437df1e353c05ba8d1bdf0f; campaign digest 61dfcc86df233db4585daa568c2e036caa16bc3a023958e4d5c886add6e77442. Actual execution workers and source mutation have NOT started.

### Blocker

Patrol denied cloning Wolf-Coin into the unregistered KRATOS project root. Its approved init-project command requires a privileged project-root helper that failed with a no-new-privileges sudo restriction in Oracle terminal. No bypass was performed. The existing remote public GitHub feature branch does not prove local installation.

### Gates still unearned

No verified Wolf-Coin executable package, broker integration, sportsbook permissions, sports/forex live operating environment, paper-performance baseline, independent fault/recovery campaign, SUP/SUP-Bit/COG active admission, Cookpit operating profile or owner-signed release is established by this preparation work.

### Resume

Recover current main and feature HEAD, original P0–P12 authority, WX candidate, Tenfold frozen campaign and Patrol current state. Resolve registered project-root access through an authorized privileged path. Only then begin P0/WX-0 implementation with bounded Tenfold tasks and Cookpit MANUAL micro/heavy; no GPT supervisor schedules. Preserve existing risks and avoid live funds.

### Verified manual workforce preparation receipts

- Tenfold Gen1 durable campaign: /home/kratos/projects/Tenfold/.workspace/wolf-coin-20261123/tenfold-authority.db, 24 nodes, revision 1, P0 BLOCKED, zero issued assignments or active leases. This records the actual Patrol blocker, not a completed milestone.
- Cookpit manual-only preparation profile: /home/kratos/projects/cookpit/.workspace/wolf-coin-preparation-20261123/profile.json. Micro and heavy preparation lanes both PASS against campaign digest 61dfcc86df233db4585daa568c2e036caa16bc3a023958e4d5c886add6e77442 and the documentary SIM receipt.
- Cookpit evidence: /home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-preparation-only/evidence. No Wolf-Coin canonical registry activation, timers, GPT supervisors, financial execution, or project-source build.
- The architecture supplement was placed in draft PR #10 for review. Original protected main remains unchanged.

### First-light source construction candidate (new — 2026-11-23)

- The public-safe, **paper-only** candidate source is on draft PR #10, with exact source head `60d02ca23dfe74324ebc89051ef862900d3b6140` (subsequent documentation commits do not change those source blobs).
- Implemented typed AccountScope/Domain/UTC/Decimal primitives, per-account durable append/replay, paper-only money reconciliation, immutable three-way football quotes, fixed 0.5% aggregate paper sports exposure and the read-only `wolf doctor` command.
- Isolated Python 3.13.5 verification: **19/19 tests passed**. All committed source file blobs were compared with the tested bytes before branch updates.
- Cookpit **manual** source micro PASS and heavy PASS; remote head and eight critical code/test file identities were independently read back.
- See `docs/FIRST_LIGHT_PROOF_2026-11-23.md` for exact commands, source digest bindings, limitations and retained KRATOS receipts.
- No installed KRATOS runtime, real provider adapter, accepted P0/P1/WX milestone, source-root registration, GPT supervisor or live-capital authority has been established. Tenfold's P0 remains BLOCKED by Patrol's required privileged root creation.

### Manual paper operator and loopback dashboard (2026-11-23 follow-up)

- Extended the first-light candidate with `wolf-paper` for **virtual** sports/trading balances, identity-fenced virtual deposits/withdrawals, status/freeze, and manually entered read-only 1X2 odds analysis. There is no live stake, broker action, funding or auto-execution endpoint.
- Added `wolf-dashboard` bound to `127.0.0.1` only, serving read-only `/sports` and `/trading` pages and GET `/health`; POST is rejected. It is a manual viewer, not a background decision worker.
- Isolated Python 3.13 test run on exactly the complete candidate: **25/25 passed**. New CLI, server and regression files were copied to the draft feature branch and every changed code/test file's Git blob hash was checked against the locally tested bytes.
- `docs/PAPER_LOCAL_RUNBOOK.md` describes native (no Docker) setup **after** authorized Patrol registration; its file identity was checked against the reviewed source. This is not a claim that KRATOS has been installed or that a real demonstration has run on that host.
- Actual required Patrol root is still missing. User-facing state: **research/paper source candidate available; KRATOS installed use and unattended real-money use NOT READY**. Tenfold campaign P0 remains BLOCKED until the intended privileged initialization succeeds, and no GPT supervisor or timer is assigned.

### 2026-11-23 resident and Patrol execution diagnosis

- Root cause of failed native registration from Oracle: user systemd oracle-node.service explicitly has NoNewPrivileges=true. Its terminal.exec subprocesses inherit NoNewPrivs: 1; Patrol's supported project_admin.create_project_root invokes sudo -n /usr/bin/install -d for the root-owned /home/kratos/projects directory. Therefore a normal authorized host terminal is needed; do not disable or bypass the existing Oracle security setting.
- New public-safe native-terminal bootstrap: scripts/kratos_patrol_paper_bootstrap.sh. It uses Patrol's own init-project, verifies ownership, obtains this review branch, validates fixed source Git object hashes, runs tests, and seeds only virtual paper balances. It has NOT been run on KRATOS.
- Paper-only Linux resident candidate: wolf_gateway/resident.py + tests/test_resident.py. It holds one instance lock per ledger, refuses corrupt/uninitialized data, serves only read-only loopback pages, and releases the kernel-held lock on forced process termination.
- 31/31 tests passed in the chat workspace, Python 3.13; three changed file Git blob SHA identities verified against this GitHub branch. This is not deployed KRATOS proof, a profitable model, sports provider permission, a live trading connector or production admission.
- Tenfold P0 still BLOCKED on KRATOS; no new GPT supervisor or schedule; no accounts connected, no real-money actions.
