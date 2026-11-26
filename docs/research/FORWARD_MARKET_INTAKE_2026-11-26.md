# Wolf-Coin forward market evidence: no-account intake and audit

Date: 2026-11-26.
Branch: `work/wolf-forward-market-intake-20261126`.
Scope: new independent market-evidence interface for the already frozen
270 2026/27 fixtures. No existing models, installed native Wolf-Coin,
paper balances, login profiles or execution permissions were modified.

## Recovered source and nonduplication check

The frozen CC0 MLP evidence is:
- `.workspace/proof-history/prelive-outcome-feedback-20261126/forward-freeze/forward-freeze-20261126.json`
- Byte SHA-256:
  `53944d9ed2869dd0114a29859df1196c525c7229f4cdac8d3c55f5b92819bec9`
- Original forecast digest:
  `decefdda4ceb1d345d620e9f88a2007498e8d40e0b076ca04dac20df3e942a88`
- 270 pending future fixtures beginning on November 28, 2026,
  frozen source cutoff November 26, 2026.

The independently ongoing
`work/wolf-forward-score-qualification-20261126` branch already
contains a Poisson 1X2 forecast candidate and paired outcome scoring,
including a model and separate frozen forecasts for the **same fixture
set**. Do not overwrite or duplicate those outputs. Its previous-year
exploratory Poisson score of Brier 0.619159346 is weaker than the
previous historical bookmaker baseline 0.578663803. Independent future
outcomes and market quotes remain required before any superiority claim.

## Public source reconnaissance — negative evidence retained

Football-Data's public weekly-fixtures page advertised a downloadable
fixture-and-odds CSV, with the upload timestamp 25/11/26 09:32 UK time.
On KRATOS, at 2026-11-26T13:42Z, fetching
`https://www.football-data.co.uk/matches/fixtures.csv` via HTTPS
redirected to `https://football-data.co.uk/matches/fixtures.csv`,
which returned an **HTML page**, content type text/html, not an odds CSV.
Exact returned bytes were preserved under owner-private:
`.workspace/proof-history/forward-market-evidence-20261126/`
with HTTP headers, local observation start/end timestamps and digest
`54451df88b54f44085f05b42ca8ef39159c4e3a4702b56ebebea80b2fbc032de`.
The pure source probe returned `REJECT_HTML_NOT_MARKET_CSV`.
**No numerical market prices were invented or admitted from it.**
A publicly described file is not proof of a byte-valid data download.

A separate current source lists Arsenal–Manchester City as Sunday
2026-11-29 at 16:30 while the frozen original forecast fixture says
2026-11-28. A schedule correction therefore must be attached as
a separate evidence artifact, not incorporated into or used to
edit the sealed original forecast. This is tested with **synthetic**
source evidence; an independently authenticated provider reschedule
has not yet been ingested. Relevant public source references:
- https://football-data.co.uk/matches/resources/contact.php
- https://www.betvictor.com/en-en/sports/240/meetings/6323610/events/2843140052

## Source-only implementation

- `wolf_lab.forward_market`:
  - Byte-pin the original forecast and validate 270 fixture identities.
  - Accept typed UTC-timestamped 1X2 quote captures and their exact
    source snapshot bytes, refusing source/hash mismatches.
  - Reject non-HTTPS sources, malformed or impossible prices, future
    timestamps, post-kickoff quotes, unrelated fixtures, contradictory
    duplicate capture IDs and non-structured source HTML.
  - Store de-vigged 1X2 probability and market overround as research
    evidence only. Include source SHA, provider, capture time, kickoff
    and fixture ID.
  - If the advertised fixture date changed, require separate source-bound
    schedule evidence, preserving the original forecast identity/date.
  - Create a hash-linked journal with owner-only immutable evidence
    snapshots and deterministic independent replay. All captures
    explicitly state `independent_provider_authentication: false`,
    `price_executable_at_provider: false`, and
    `financial_action_authorized: false`.
  - This is intentionally **not** an independently signed bookmaker
    snapshot service: a local hash can prove file identity but cannot
    establish external quote provenance, timestamp authenticity or
    live execution.
- `wolf_lab.forward_market_cli`:
  - `probe --raw PATH`: inspect a downloaded source's file bytes.
  - `capture --freeze FROZEN --evidence-dir PRIVATE --quote QUOTE.json
    --source-evidence SOURCE.json [--schedule-evidence SCHEDULE.json]`:
    ingest verified-by-local-hash source/typed quote into next immutable
    journal version.
  - `verify --freeze FROZEN --evidence-dir PRIVATE`: restart-replay
    recorded evidence; refuse numbering gaps, tampering or missing bytes.
  - No network fetch, account credential access, trade order, betting
    session, installer or financial authorization is part of this CLI.
    New bookmaker adapters must supply genuine origin evidence and
    explicitly qualify provenance before scoring as a reliable baseline.

## Qualification verdict

- 11 targeted source-evidence tests + 3 CLI end-to-end tests: PASS.
- Complete existing Wolf source test suite: **468/468 PASS**.
  This includes 4 new source-bound public HTML and HTTP transport-date tests.
- Original future-forecast byte SHA and event identity preserved.
- Public weekly-odds CSV retrieval: **FAILED (HTML response)**.
- Source-bound public *aggregator* 1X2 market quote captures: **1**
  (captured after source reconnaissance; separate source addendum below).
  This is not a direct bookmaker-authenticated or executable price.
- Actual future settled match results in the 270 frozen window: **0** as
  of this session's November 26, 2026 timestamp.
- Market-relative future proper-score superiority: **NOT TESTABLE YET**,
  not silently marked passed.
- New model promotion, real-account profit and live financial execution:
  **NOT AUTHORIZED OR PROVEN BY THESE TESTS**.

## Next valid acceptance boundary

Preserve both frozen MLP and Poisson forecasts. Obtain and independently
authenticate valid source bytes for actual pre-match 1X2 quotes; reconcile
changed fixture schedules with evidence; later use independently
observed, post-match outcomes to score both models against each other
and the quote baseline on exactly matching fixture identities, with
source timestamps before kickoff. No replaying already exposed
historical windows can replace an untouched future holdout.

This extends existing Wolf-Coin protocol/evidence. No source
of truth was overwritten. **Contribution type: New + Verification +
Update existing documentation.**


## Verified follow-up: first real public quote, no financial action

After the source's failed CSV download, an independent public web
listing was retrieved successfully from TipsterArea on KRATOS at
**2026-11-26 13:48:17 UTC**. Its original HTML, HTTPS response headers
and observed source time are retained in the existing owner-private
`.workspace/proof-history/forward-market-evidence-20261126/` folder;
no raw third-party HTML was added to Git.

Source: `https://tipsterarea.com/match/arsenal-manchester-city-premier-league-england-957595`

- Source HTML SHA-256:
  `3db1955f2afa9768a74297b729d078b00fc4a80989c7616eac8191081adcada4`
- HTTP response headers SHA-256:
  `30819d14723b2807fd9f14eac8ea7f392db13059e863263e8cbfa40d444745d8`
- Original frozen fixture identity:
  `2026-11-28|arsenal|manchester city`
- Public listing's current scheduled kickoff:
  `2026-11-29T16:30:00Z`. The old, frozen identity was preserved,
  while the changed schedule was independently represented by the
  source-bound page evidence. No forecast was rewritten.
- Aggregator's published **betfair** Standard 1X2 row:
  home 1.95; draw 3.70; away 3.60.
- De-vigged market class probabilities:
  home 0.483396842678; draw 0.254763200871;
  away 0.261839956451.
- Immutable original captured quote journal:
  `verified/journal-000001.json`.
- Journal SHA-256:
  `60e430d900fe3eb29f979818935563833fabb7b04988e86a66a36a8c42eac8d2`.
- Additive, separately immutable HTTP Date attestation:
  `LOCAL_HTTP_DATE_PROOF_RECORDED` for the same capture ID; does not
  rewrite the earlier journal. Verification rechecks exact HTTP header
  bytes and their reported source date against the typed observation.
- CLI replay returned:
  `SEALED_MARKET_JOURNAL_VERIFIED`,
  `quotes_recorded=1`,
  `http_server_date_attestations_checked=1`.

**Limit:** TipsterArea is an aggregator. The quote is labeled as an
aggregator-published Betfair price, **not a direct authenticated Betfair
API quote, proof of available execution, an independent cryptographic
timestamp, a verified profit opportunity, or a decision to bet**.
Hashing local HTML and transport headers proves recorded byte identity
only. The next eligibility check must still compare actual
provider-reconciled pre-match prices and independently settled results
against the original frozen predictions.

Test additions:
- Extract Standard 1X2 and kickoff time directly from the pinned HTML,
  refuse price/fixture/date contradictions.
- Preserve 28->29 November rescheduling with extra source evidence.
- Bind the HTTP Date header to the observed time as an append-only,
  independently replayed attestation.
- Refuse altered transport dates or tampered attestation JSON.
- Preserve all 11 generic and 3 CLI replay tests.
- **468/468** complete research-suite tests pass.

Revised contribution: new public-source market evidence captured and
independently byte-verified (provisional origin), with unchanged
model-promotion and real-account funding gates.

## Cross-artifact evidence reconciliation follow-up

The isolated `work/wolf-forward-evidence-reconciliation-20261126`
branch extends the committed market intake without changing the separate
uncommitted forward-score worktree or its artifacts. The read-only
`wolf_lab.forward_evidence_reconcile` command byte-pins both frozen
forecast universes, checks the source and paired report seals, validates
fixture membership, coverage, capture chronology and per-fixture paired
Brier arithmetic, and replays the market evidence. A changed fixture date
is counted separately, not silently joined to an original-date result.
This is a local evidence coverage audit, not a substitute for verification
of raw settlement provenance or a market-relative performance test.

Journal replay now also validates every historical snapshot against the
latest replayed prefix and checks that each HTTP Date attestation links
to a valid journal prefix containing its capture. A valid latest snapshot
can no longer conceal altered earlier journal versions.

Regression: 475/475 passed, including seven new checks and a synthetic
post-match arithmetic/rescheduling case. Actual private artifact:
`.workspace/proof-history/forward-evidence-reconciliation-20261126/reconciliation.json`;
file SHA-256 `c60df9411bf3d2ff37d501c88d165827638fd4fda82100e4b5ac6da88b5b2857`.
The verified local coverage is 270 frozen fixtures, 0 paired outcomes,
270 pending, 1 provisional quote fixture (rescheduled), 269 without quote
evidence, and 1 HTTP Date attestation. No model parameters, forecasts,
application state, account data or installed packages were changed.
Independent source authentication, actual-provider reconciliation and
predictive superiority remain unproven. Contribution: correction,
verification and update existing documentation.
