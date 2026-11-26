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
- Complete existing Wolf source test suite: **464/464 PASS**.
- Original future-forecast byte SHA and event identity preserved.
- Public weekly-odds CSV retrieval: **FAILED (HTML response)**.
- Genuine independent pre-kickoff market quote captures: **0**.
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
