# Wolf-Coin / CC0 neural research — after the source freeze

**Status:** offline CC0 research implementation, not financial strategy or SUP/SUP-Bit production deployment.
**Source freeze:** `170a555991910fd3db525c2070ace88568b6f0b4` on November 23, 2026. It committed architecture, features, model selection and tests **before** fetching the future-data file. Those weights and hyperparameters are retained unchanged.

## Source and rights

- CC0-1.0 public-domain results from `https://github.com/openfootball/football.json` at Git commit `e6744429ee395bc86f247348c6184bb08d4eb361`.
- Exact CC0 license SHA-256: `36ffd9dc085d529a7e60e1276d73ae5a030b020313e6c5408593a6ae2af39673`.
- Training 2017/18–2023/24: **2,660 matches**. Validation 2024/25: **380 matches**. Neither involved the restricted Football-Data bookmaker dataset.
- 2025/26 prior-history-only file was **353/380 scored** and is incomplete. Its scored matches are used only for constructing lagged feature history for the next season.
- After freeze, first pinned 2026/27 result source digest: `bb91f0ab3e8359df163bb9ec98549bfed85e200dd4c32f3bd606b5890d932dd2`. Only **45/380 fixtures had full-time scores**, latest result **September 20, 2026** in the source snapshot. 335 are unscored. Do not assert the whole season has been evaluated.
- Post-freeze quality audit (private comparison **only**, not ML training): **760/760 exact fixture and final-score matches, zero conflicts**, against two privately retained independent Football-Data CSV season files. Audit file SHA-256 `ac135ee5c3fb5ebbfea94b68843b54b1c08c454ae56ae790a9f0e3c108d1f4af`. The bookmaker service's own usage policy is private/academic analysis only, not an AI training source.

## Frozen model and first holdout result

- Model: NumPy 8-unit tanh MLP, deterministic seed 17, 350 full-batch updates; compared with a linear forecast. CPU research only, **not SUP-Bit neural training**.
- Frozen model artifact SHA-256 `2eb587952d5fb72dd25fcaa50aac9b46d6c4e6d3be33a02b502bb7e5a09a3fba`; internally sealed digest `sha256:9b0e22f38810950b5920d4ff52ff6c2dbf96691c7e414946dd0e4f9452e48ef7`.
- 2024/25 validation Brier (lower better): empirical class prior **0.655478614**, linear **0.623560457**, MLP **0.623347533**. The MLP is barely better than linear. Earlier independently measured bookmaker-derived Brier for 2024/25 was **0.578663803**, much better than either model. Thus no market edge.
- First truly later evaluation: 45 scored 2026/27 fixtures, **MLP Brier 0.611911853 and log-loss 1.023508094**; historical class-prior Brier **0.657353561** and log-loss **1.083257733**. The paired Brier improvement is +0.045441708, but **match-day clustered 5,000-sample bootstrap 95% percentile interval spans -0.050237688 through +0.158399450**. This includes zero.
- Outcome: **insufficient evidence** to claim repeatable prediction superiority, let alone financial returns. No bookmaker quotes, real bets, virtual bets or funding actions were used in this experiment.
- Holdout audit SHA-256 `fd3c4c35bcfa4c828681447b0681e196eaf99f23631b4cd59b20ad6fa577cb69`. The stored evidence is under `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/cc0-neural-20261123/`.

## Actual SUP Director

- Scoped **CC0 outcome-only** machine source-qualification receipt matched 760 external scores and upstream CC0 rights. This is a **machine proof**, not an independently signed human approval.
- The existing G5 SUP Director accepted the exact source/product/evidence-bound receipt and advanced to **`AWAIT_CAPABILITY_SNAPSHOT`**: Cookpit, Formula, Simulation, SRG, Soup and resources still need separately authenticated generation bindings.
- Director digest `sha256:d3889b05505bbd4672c9d9c553662d1f2d966f66e64ce5e3b81ff8e4171ee8fa`; output explicitly shows `training_executed=false`, `authority_granted=false`, `deployment_authority=false`. It does not approve this model or its financial use.
- Private SUP intake, receipt, and result under `.workspace/research/sup-sup-bit-forecast-20261123/cc0-mlp-170a555/`. No GPT supervisor was created.

## Engineering and release boundary

The source adds a read-only `/neural` evidence view to the existing loopback-only paper dashboard. No model weights are loaded into the service, and there are no model-triggered orders, payments, cashouts or third-party requests. The core user service has no new NumPy dependency; NumPy is optional for separate offline research.

**No financial profitability gate is proven; no real-money or automated betting admission.** Further work needs current SUP capability snapshots, fresh independently verified match outcomes/quotes, larger untouched scoring windows, source/venue authorization and independent release acceptance.


## Native KRATOS release — 0.1.0a4

- Exact tested implementation HEAD: `f5e7acac87db6e30d7bd4fa928eb7036cf5c1680`. The previous frozen source/head `170a555` and external 2026/27 evidence are unchanged.
- Offline, standalone wheel `wolf_coin_core-0.1.0a4-py3-none-any.whl` SHA-256 `f03186cc39fc5ecedb431e7e27ab81c078aa8a09508cf92dcc01daef1b707249`. Installed native paper console at `/home/kratos/.local/share/wolf-coin-paper/releases/f5e7acac87db6e30d7bd4fa928eb7036cf5c1680/venv` without pulling NumPy into the resident service.
- The separately installed offline research runner replayed exactly the initial source-bound holdout output. The model weights were not refitted for this re-run.
- `wolf-coin-paper-preview.service` remains user-level, enabled, `NoNewPrivileges=true`, bound exclusively to `127.0.0.1:18766`. Routes `/sports`, `/trading`, `/lab`, `/forecast`, `/neural`, `/funding`, `/health` returned HTTP 200. The new `/neural` page shows the partial 45-match evidence, wide confidence interval and SUP stage. `POST /neural` returns HTTP 405 and no financial action route exists.
- The previous installed package, original paper-ledger data and prior service file are preserved; latest rollback service receipt is `/home/kratos/projects/Wolf-Coin/.workspace/proof-history/cc0-neural-20261123/previous-paper-unit.service`.
- The Neural page was opened in Brave on KRATOS's existing XFCE desktop session.
- **Cookpit manual micro PASS**, 24 focused source and boundary tests, frozen model/source digest, independent 760-result check, actual SUP stage; receipt `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-cc0-neural-score-lab/evidence/20261123T131310Z-micro-0219b6f12556.json`.
- **Cookpit manual heavy PASS**, **251/251 tests**, exact wheel digest, pinned native service and localhost-only no-money controls; receipt `/home/kratos/.local/state/ttg-cookpit/projects/wolf-coin-cc0-neural-score-lab/evidence/20261123T131315Z-heavy-0219b6f12556.json`.
- No GPT supervisor created, no Tenfold money/training milestone promoted, no SUP-Bit neural inference asserted, and no sportsbook/broker permissions or accounts touched.

**Final decision:** This is a verified source-bound **offline neural score research tool** and safe read-only UI, **not** a positive-EV financial strategy or a funding-ready release. The source data 2026/27 is stale/partial, and the match-day bootstrap interval crosses zero.


## SUP capability-snapshot closure (2026-11-23)

**Completed the missing SUP_SIM input**, through the existing SUP G5 Director rather than an independent simulator. This is **frozen-pin contract verification, not independently signed production authority**.

The read-only audit in `scripts/sup_capability_snapshot.py` verified Git commit objects for the exact pinned Cookpit `0d778f2f7591ecf65001b78cc829f38bc7a1468d`, Formula `f4edde73eaace58d6f416fae43d2b5cbb6caec6c`, Sergeant `126eeea5a70a0723a1bfb65b2a5dbeb6a84cf2e0`, TTG-Simulation reviewed source `b142b3dbfef428e43311fcc6b6b37189a82a0449` and evidence commit `3078fbc4ff2ee7a8a7286cefba73d59488dfc11c`. The canonical SUP simulation generation `sha256:3e7d230de3e698c17073add1909066d3220f4c39ab90f335e8767799f98db921` was recovered from the SUP binding. The owner-fork Soup commit `088c4272a6b1102908d85afe2b03e53860d56be8` was verified through GitHub. No donor authority transfer or command execution was enabled.

**All active local repository HEADs differ from the frozen SUP pins.** Pinned Git objects are available, but an available frozen generation does **not** prove the latest owner software is currently approved, or that an independent human signed release acceptance.

Soup's LLM-oriented SFT/LoRA/preference/distillation training methods have **no proved tabular 1X2 adapter**. The earlier SUP-Bit observation only measured fit for a small NumPy CPU workload; that fit cannot be assigned to Soup's unrelated methods. The snapshot conservatively marked all eight borrowed training-method fits as unknown. The native SUP_SIM returned **0 of 10 eligible candidates**: eight hardware/task fit unproved, two donor-unsupported.

- Previous Director: `AWAIT_CAPABILITY_SNAPSHOT`.
- New Director: **`NO_VIABLE_NEURAL_ROUTE`**, digest `sha256:1f135655dc3be8552dfcc2b3a181821643d7bcc3799cc410f1c7468953482bd2`. Native SUP_SIM digest `sha256:da677fc33963078ae8cfda89ac6247543082fdcb65a01e374231d9f8643d7f5c`.
- Correct new owner: **Full Formula / Wolf-Coin Director** for qualified tabular training-route development, not execution promotion.
- Native negative controls refused stale Cookpit generation, enabled Soup execution, and mismatched learning source.
- No SUP training, Tenfold lease, funding, live betting or independent signed acceptance was asserted.

The immutable private evidence is under `/home/kratos/projects/Wolf-Coin/.workspace/research/sup-sup-bit-forecast-20261123/cc0-mlp-170a555/verified-capability-snapshot-20261123/`. Capability completion receipt SHA-256 `e83c4298c48a07ff85d41814dc57e72ae3bdef2f5c45c169b26ae885e2486fe4`; saved SUP Director result file SHA-256 `1daec246673fde6312dcb115fdc01aab3a6383f1c38e54f562146d46a770837e`; SUP_SIM result file SHA-256 `2f40c2df998ec5e6ab51dfa1a28924a9d86674f6d9d5ad678bb8e0d910fd5d97`.

The running read-only `/neural` UI now uses new immutable private summary `neural-summary-sup-snapshot-20261123.json`, SHA-256 `fb53c61d3a52eac67183de84e6f1bb7666c3159dd18d53723fd4ae6a9c0f8356`, and displays `NO_VIABLE_NEURAL_ROUTE`. The previous summary, native wheel `0.1.0a4`, pinned model, paper ledger and rollback unit remain preserved. Service is still loopback `127.0.0.1:18766`, PAPER-only, and POST is denied.

**Gate disposition:** missing capability snapshot resolved, but neither a production-compatible SUP route nor real-money authorization is complete.
