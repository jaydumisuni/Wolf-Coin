# Wolf-Coin 0.9.7-dev — read-only account recovery candidate

ATHENA's installed v0.9.6 showed the actual authenticated account wallet with
K3.50, while Wolf's two registered sports accounts were PAUSED and no financial
observations had been stored. No actual wager or funds movement was performed.

Corrections: distinguish startup revalidation from an explicitly owner-paused
account; revalidate eligible profiles rather than exclude them from refresh;
recognize a compact, unlabeled currency amount in a bounded account panel only
when supported by visible account controls and a unique currency amount; retain
same-origin account/statement pages during read-only refresh; prevent skipped
snapshots from triggering a stale follow-up; ensure desktop registration precedes
capture. Android and desktop observation scripts are byte-identical. Android
read-only refresh waits for the matching account, origin and complete document,
rather than a fixed 170ms delay. No financial execution or learning capability
was added by this change.

Proof: source DOM and session-policy checks passed, including public price,
ambiguous amounts, sign-in page and late panel cases. A real isolated Chromium
fixture and signed backend recovered PAUSED → ACTIVE with synthetic K3.50,
two recorded observations, and the same account page preserved. The fixture
simulates host-startup revalidation; it is not a real provider settlement or
physical Android test. Earlier attempts exposed a sandbox-helper permission
failure, an occupied fixture-only debugging port, and concatenated button
text; the final controlled run uses a distinct profile/port and semantic
control labels. Private evidence: `.workspace/proof-history/session-recovery-20261126/`.

The release version is 0.9.7-dev (Android versionCode 19). Do not deploy a preview
or omit the owner-held D-XQT and exact previously installed backend source.
Production package identity, installed real-account readback and Android runtime
qualification remain separate acceptance gates until proven. Contribution:
correction, verification and update existing frontend documentation.
