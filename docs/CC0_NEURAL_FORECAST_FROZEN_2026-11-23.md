# Wolf-Coin — CC0 neural research freeze before 2026/27 holdout

**Frozen on 2026-11-23 before retrieving 2026/27.** No real-money authority; not a SUP or SUP-Bit production release.

## Source qualification distinction

The prior Football-Data bookmaker CSV source is restricted to private and academic research and excludes AI data-training projects. It is **not used for neural training**. The only neural source is OpenFootball's CC0-1.0 public-domain league-results dataset: https://github.com/openfootball/football.json at immutable upstream revision `e6744429ee395bc86f247348c6184bb08d4eb361`. The upstream CC0 license SHA-256 is `36ffd9dc085d529a7e60e1276d73ae5a030b020313e6c5408593a6ae2af39673`.

Exact local input hashes are in `wolf_lab/cc0_pipeline.py` (2017/18 through 2025/26). The nine season source documents are frozen privately in Wolf-Coin `.workspace/research/external/openfootball-cc0-20261123/`, not included in the public repo. 2017/18 through 2024/25 each have 380 scored results. **The 2025/26 source is incomplete: 353/380 scored.** This season is only pre-2026/27 feature-history context, *not neural training or validation*.

Licensing and integrity review supports **private CC0 neural research**, not signed independent SUP acceptance or proof that every match result is authoritative. It does not authorize sportsbook access.

## Frozen experiment

- Train: 2,660 CC0 2017/18–2023/24 Premier League results. Validation: 380 CC0 2024/25 results.
- Features: previous-date home and away goals, points, recent form, experience and fixed home-role indicator. Same-day labels cannot inform other fixtures of that day.
- Baseline: empirically learned training-class prior.
- Neural: deterministic NumPy 8-unit tanh MLP, seed 17, 350 full-batch gradient iterations, learning rate 0.07 and L2 0.015; compared against multinomial linear model with the same data.
- Selection: lowest Brier then log-loss as tiebreak; at least 0.012 Brier improvement and 0.005 log-loss improvement against class prior or ABSTAIN.
- Validation: class prior Brier 0.655478614 / log-loss 1.080844008; linear 0.623560457 / 1.036030400; MLP 0.623347533 / 1.036068586. The MLP is selected for **fresh proper scoring only**. It barely differs from linear and does not beat previously observed bookmaker baseline Brier 0.578663803.
- Predeclared holdout: first pinned 2026/27 OpenFootball snapshot, evaluated once with frozen trained weights. Retain the 27 2025/26 unscored fixtures as missing; do not fabricate scores.
- The partial-season holdout score must report coverage and cannot validate profit, bookmaker availability, SUP-Bit neural quality or real-money release.

## Gates

Allowed: frozen CC0 model training, replay, native CPU timing and proper-score research. Blocked: signed source-independent review, SUP Director training admission, SUP-Bit adaptation, market-relative betting edge, venue permission and funding. Real/virtual financial execution is absent.

Final partial-season evidence will be appended after this specification is committed. No changes to frozen model hyperparameters or selection law after holdout retrieval.
