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

## 2026-11-27 — installed development deployment

Source freeze: `3add4cda6f90d6955fb8b4b210f535af3e68d9e5`.

- **KRATOS:** Builder Linux DEB succeeded; system `wolf-coin` upgraded
  from 0.9.6~dev1 to 0.9.7~dev. Actual installed application payload
  matches the staged source; the visible native window and backend
  database were confirmed. The new package uses `/opt/Wolf-Coin` and
  the system alternative points there. The DEB carried the setuid
  sandbox bit, but the installed mode was 0755; restored root-owned
  4755 to match the established installation before normal launch.
  Package SHA-256: `e56f771789d22351892e9c7fb152f3e7ce04fb90dd353baa6548d3c9c9ee7880`.
  Previous DEB retained for rollback. Builder packaging used the
  cached runtime and existing shared tooling, not a new installer engine.
- **ATHENA:** Builder windows-exe target completed with exit 0 after
  a retry outside the initial terminal timeout. Standard Builder NSIS
  installer completed exit 0. Installed exe file version 0.9.7-dev;
  main window running from the normal per-user installation path.
  Installed exe, ASAR, and unpacked backend store matched the Builder
  output byte-for-byte. Installer SHA-256:
  `7411038eb6c49367c015f9381860e884464c8a34d185cfecfb3b21322daf69c9`.
  Existing two registered account records were preserved; both remain
  PAUSED without observed balances at this readback. Actual wallet
  synchronization is NOT accepted by the installation check. Windows
  development installer is unsigned. Builder log and artifact retained
  in the existing local Wolf-Coin release directory.
- **Android:** Builder release APK compiled; existing main application
  on emulator-5580 (Android 15) was 0.9.3-dev, code 14, signed with the
  original main-app debug certificate. Matching-key `adb install -r`
  succeeded: 0.9.7-dev, code 19, original firstInstallTime unchanged,
  installed APK hash matched the signed package. Overview rendered
  with 13 retained account registrations after a transient emulator
  System UI ANR. No uninstall or data clear was performed. The separate
  QA variant (0.9.6, distinct signing key) remains untouched. Main APK
  SHA-256: `df5159277423dde0bcc4294acca55d6e0dc772c358cc93aff20979cfa92db738`.
  No physical Android device was connected. This is development signing,
  not production distribution qualification.

Installation gate passed on both desktops and the existing Android
emulator. Actual provider synchronization, live settlement, autonomous
financial execution and profitability are outside this deployment proof
and remain unverified. No funds moved. Local proof:
`.workspace/proof-history/session-recovery-20261126/deployment-linux-android.txt`.

## 2026-11-27 — actual ATHENA read-only wallet acceptance

After the independent Oracle desktop-control recovery, all 15 installed donor
files matched their manifest, and Oracle pointer actions were accepted and
visibly changed the native application. No Oracle source or policy changes
were made by this Wolf-Coin session.

Actual authenticated provider account panel showed ZMW 3.50. Installed
v0.9.7-dev captured two observations and reported ACTIVE with cash_balance
3.5 in the persistent application database. The provider statement page
showed an empty history and the betslip was empty. A clean application
restart preserved three observations and the last-known amount; host startup
correctly required revalidation. Reopening the preserved browser statement
page and its account panel, without credentials or another manual login,
produced a fourth observation and returned the backend session to ACTIVE.
Latest verified observation: 2026-11-27T02:21:40.468000+00:00, balance 3.5,
transaction count 0. The account panel was opened manually; unattended
startup revalidation without this interaction is not established. No
transaction capture or real settlement qualification can be claimed from
an empty provider statement. No bet, deposit, withdrawal, or trade was made.
Android acceptance remains deferred per owner instruction. Contribution:
verification and update existing documentation.

## 2026-11-27 — accounting and installed-package qualification

- Ten isolated accounting regressions passed both on the separate native
  readback source branch (87e1bcc) and on the actual installed KRATOS backend
  loaded from `/opt/Wolf-Coin/resources/app/backend-runtime`. These cover
  ingestion of reported records, pending/settled deduplication, conflict
  rejection, history isolation/pagination and currency boundaries.
- The installed KRATOS executable (not source Electron) passed the existing
  compact wallet/revalidation fixture, using a loopback-only website, separate
  profile and backend, and normal Chromium sandbox. The synthetic amount was
  3.50; session PAUSED -> ACTIVE, two observations, same account page retained.
- Six existing readback regressions on 87e1bcc passed with synthetic evidence.
  They establish reported status linkage, not external settlement truth or
  realized profit. That branch is distinct from the installed backend.
- Six historical evidence-integrity regressions passed: coverage, sealed
  report identity, future-date rejection and journal immutability. No model
  optimization or claim of predictive profitability was performed.
- Android emulator still runs v0.9.7-dev, code 19. Installed APK hash matches
  the retained release, and its packaged observer is byte-identical to the
  desktop observer. This is artifact/runtime smoke evidence, not a native
  Android account-flow or physical device acceptance.

Live provider transaction ingestion and transaction-derived P/L remain
unqualified: the previously observed real account statement contained no
transactions. Betway authentication, unattended restart recovery and live
settlement have not been established. Production qualification is not claimed.
No new financial actions or autonomous execution capabilities were introduced.
Proof logs: `ledger-qualification.log`, `installed-ledger-qualification.log`,
`installed-native-recovery.log`, `settlement-evidence-qualification.log`,
`historical-evidence-integrity.log` in the existing project proof directory.
Contribution: verification; update existing documentation.

## 2026-11-27 — v0.9.8-dev chat deployment and acceptance

Source generation: eea8b97090faa213ee96602c85bf44a256cea4ac.
The Wolf logo opens the native product's conversation; Android uses the
floating Talk to Wolf launcher and a compact browser-header entry point.
Wolf is the product identity; iAM-derived cognition is an internal faculty,
not a separate assistant or identity.

- Existing Builder Windows, Linux and Android targets completed with exit
  code 0. Windows and Android terminal timeouts were reconciled against
  actual package/build evidence. Android used the existing development key.
- ATHENA: installed 0.9.8-dev, ASAR hash matched the staged artifact
  (8435b055cd850f431b081b77be46d69c2e9b9c5317c5cd5ffd45198b72ba465d).
  Actual installed conversation showed a user greeting and Wolf's response.
  Oracle proof run: wolf-v098-windows-visible.
- KRATOS: installed 0.9.8~dev, HTML payload matched frozen desktop assembly
  (627e789dbf7b4735b079b64c9230b2b6d038c09e4e7858daa94a018395d2f06d).
  Restored the package's root-owned Chromium sandbox mode 4755.
  Installed executable passed the chat navigation, preference, reopen
  and responsive-layout test in an isolated test profile.
  Proof: v098-chat-installed-linux.log.
- Android emulator: installed versionCode 20 and base APK matched retained
  release SHA-256 3cadc2424963b6934d052d66a5c902408d3449db5ccbca86569e9b1fb1704e05.
  Actual launcher opened the conversation, typed message was accepted,
  and capability response was visibly rendered. Accessibility XML omitted
  scroll-log text; screenshot independently confirmed the response.
  Oracle proof run: wolf-v098-android-chat-proof.
  Physical Android device acceptance not performed.

COG currentness checked against Cookpit main
5f10390c1806ee678b393fc4f3c25ff801536cad and G0-G6 draft
8dce551b8b12d5b626b213474587c73b93bd7846. iAM architecture source
62102d6629113f530a50691368da909324cb3d91. The existing admission
record remains HOLD / NO-GO pending independent owner and gate evidence.
The current local conversation/typed workspace router is not the
qualified iAM-derived cognition runtime. No native COG activation or
new financial execution capability was introduced. Do not infer full
natural-language or autonomous financial capability from chat acceptance.

Contribution: verification; update existing documentation.

## 2026-11-27 — v0.9.9-dev Lumi-style chat correction and deployment

Frozen source: 462d3f0b2e1569a71761881c3e83061f4995463d.
Reference: existing Lumi Assistant UI at Lumi-DM 345583f. Wolf retains
its own identity and mobile launcher; shared frontend now uses a compact
non-blocking glass panel, header, message composer, clear/close and
Lumi-style response actions. Feedback remains local, not durable learning.

Builder completed all three existing targets. The first Linux build was
interrupted and recovered using the existing stage. Windows Builder's
artifact-discovery log named a retained older installer; the newly built
0.9.9-dev installer and executable were independently identified by
version and installation/ASAR readback. No ad hoc installer builder used.

- Linux DEB SHA-256:
  903e173c38587df1ed1a352d8f4c5883fec4ec1faa22d07ba5ff9302751a2800.
  Installed version 0.9.9~dev; HTML matched frozen assembly
  9e171055ab1c0bed4e9c8cd6eb90c323ff50ab83078d8737cb88f26261f9be49.
  Restored the verified Chromium sandbox mode 4755 to match DEB metadata.
  Installed isolated chat interaction test passed; proof log
  v099-chat-installed-linux.log.
- Windows installer SHA-256:
  3188767058d416f56b424ab074ad77bc195f32e6fd0c5e6fb2e2d9c4b7142234.
  Installed v0.9.9-dev ASAR matched Builder output:
  416bb29928c664fd3ffd1da5fd18a04929689228f096406067197c8d49208f3d.
  Installed executable launched and passed isolated chat interaction
  suite (existing stage v099-chat-native-proof/test.log).
  Prior live application profile and backend were not used for QA.
- Android APK SHA-256:
  8b68c41f004fc503df8d3d25c091ac21536b23544dba5606955f6231c13374ce.
  Frozen HTML matched APK asset. Installed versionCode 21 and base APK
  hash matched retained release. Existing lab AVD was restarted without
  downloading another system image. Actual mobile launcher, message entry,
  short greeting and six response controls visibly confirmed.
  Oracle screenshot proof: wolf-v099-android-chat.
  No physical Android device was connected. Development signing unchanged.

Desktop interaction checks covered navigation, workspace preferences,
reopening the conversation, responsive launcher, feedback exclusivity,
Sources, More, and clear conversation. Copy/share/export were implemented
but their native platform side effects were not separately verified.
Visual comparison confirms the compact Lumi-style design; pixel-exact
identity with Lumi is not claimed. No additional financial execution
capabilities were introduced. Full iAM-derived cognitive faculty remains
unintegrated: existing COG admission record remains HOLD / NO-GO.
This closes the corrected chat deployment, not all production gates.
Contribution: correction + verification; update existing documentation.

## 2026-11-27 — product-scoped COG read-only qualification

Recovered the existing Cookpit automatic Foundry identity for Wolf-Coin.
The live observer reported a new product, SHADOW, not registered active,
with only authority binding and self-model interrogation complete.

Ran the existing product-scoped qualification-request command from
Cookpit's deployed main-runtime source dafe00d. All six pre-assurance
gates passed. Sergeant (existing checkout 3a19dff) ran its documented
diff-review against that exact request: PASS, zero findings. The
Foundry's assurance and qualify-product commands then produced a
QUALIFIED receipt with all seven gates complete, no pending gates,
eligible_for_activation=true and active=false.

Evidence root on KRATOS:
~/projects/cookpit/.workspace/proof-history/wolf-cog-readonly-qualification-20261127/
- request digest: 79b584c2881183d1c8134735dd875a01c6262b1b273ade2efc9d9de140d4d4a2
- candidate: f48bec2661c5aad9344716cb735805ab028291f2111fa03e136f2ebfd949ef5a
- snapshot: 8dbcea1ba093ab6517448c3b2e7a08c365fd241d3db1532f7e4f659c86d65c50
- receipt digest: c81d9a17e5f27a85b097ea7c293f592ec4adbda16a0028ca64d8ca97d3bd8c34
- receipt SHA-256: 43f8e3872dc5c80f2a5e0873e114614df0a434f1ba26515167a707dc7a88ca4e

This qualifies the existing read-only self-model contract at that exact
evidence generation; it does not certify native application integration,
advanced G0-G6 cognition, financial execution, durable learning or
performance improvements. Recheck current target binding before any
separately admitted read-only registration. No production registry or
application runtime was changed. G6 remains HOLD/NO-GO in the authoritative
Cookpit candidate record, and the installed pending status remains truthful.
No Windows/Linux/Android application build was performed for cognition.
Contribution: qualification progress and evidence recovery, not closure.

## 2026-11-27 — continuation reconciliation: approved UI, native effects, admission

### Approved default UI reference

The owner approved the Lumi-style conversation UI as the default for
COG-equipped products with conversation surfaces. Recover the actual shared
source instead of requesting another video:
- Cookpit PR #112, head 909df2b83c70907fdecb7092b6c25daa6e1328a3:
  ui/cog-conversation (reusable shell, icons, host adapter and smoke fixture).
- OS-playbook PR #3, head a5be68492afb21fb404116b86c6cf28d7f71dcf1:
  05_STANDARDS/UI_UX.md.
Both PRs remain open; Cookpit #112 is draft. Two fixture identities passed
desktop/mobile interaction tests. These are not yet mainline fleet changes.

### Native conversation response effects

Windows and Linux installed v0.9.9-dev independently passed actual OS
clipboard readback, Share's clipboard fallback and exact filesystem export
(21-byte greeting). Linux evidence: v099-native-effects.pROzKF/effects.log
under this recovery's proof-history directory. Windows evidence: existing
Builder stage v099-chat-effects-519e3d018f574e6da709960b136b34e0/effects.log.
Android emulator v0.9.9-dev Copy was verified by system paste into the composer.

Source dc10022 implements Android-native ACTION_SEND chooser and
ACTION_CREATE_DOCUMENT export through the trusted UI bridge, with cancellation
and write-result handling. Existing Builder produced Android v0.9.10-dev
(versionCode 22); builder-v0910-android.exit is 0. The frozen Android asset
SHA-256 is 1d95c1f14341910b0653eca4d7cc49ca28538147c0de6ee82fec5b3bb169d3d7.
The emulator still reports v0.9.9-dev/code 21. Do not mistake the new
unsigned build for an installed or accepted release. Remaining Android
work: existing dev signing, install, verify actual share chooser and
document bytes, then physical-device acceptance when available.

### First-time read-only registration correction

Cookpit PR #113, head f7c9e2edd6cc67d4cc62355a1845269568e04078, adds explicit
first-time admission for a current fully qualified product-scoped receipt.
The existing refresh path remains unchanged by default. All 68 focused
Foundry/CLI tests passed. Actual Wolf receipt succeeded in an isolated
registry candidate, returning Wolf's evidence-bound self-subject; all 24
existing registration rows remained unchanged. No production registry write.

Under the Cookpit qualification evidence root recorded above:
- registry-admission-candidate.json SHA-256:
  d72c3e6d2f6f667e1a2ffd7a0717940554bf95b25c2ebe10b2fe95efc75ca96b
- candidate-identity-query.json SHA-256:
  a9bdab8aa52cbc583261f8ccc150024ccdac24883f076901f4e1ae935a65d138
- first-admission-tests.log: 68 passed.
- live auto-registry.json SHA-256 at reconciliation:
  9baaacdeb1ecc7ecf1129712c5462e7953acf8df8f64ad5bcadd7a3ae3cac8f9

PR #113 remains open. The candidate is not live activation. Next cognition
frontier is independent review and governed read-only registry promotion,
then native product binding and installed acceptance on Windows, Linux and
Android. Recheck the receipt's current candidate/snapshot binding before
promotion. Advanced G0-G6 admission remains HOLD/NO-GO; do not change the
pending indicator to imply unavailable cognition. No production effect or
learning authority is granted by this work.

Contribution: documentation reconciliation; update existing handoff. No
additional runtime, UI or registry changes in this reconciliation.

### Explicit read/write capability scope

The approved product direction is Wolf as the self-subject of its integrated
iAM/COG faculty, with conversation as an interface to its actual host
capabilities, not a separate assistant. Read and write are distinct:
- Implemented local chat reads: native account status, recorded wallet
  observations and transaction history; evidence/source attribution.
- Implemented local workspace writes: screen/dialog navigation, opening a
  browser tab, sidebar state, notification and tab-restoration preferences,
  theme and search engine. Existing application handlers and state readback
  are reused. These are not arbitrary backend, account or credential writes.
- The qualified read-only Foundry contract and candidate registry do not
  grant effect authority. Native read-only iAM binding remains outstanding.
- Broader host-governed read/write design is already defined by
  TTG-decisions/decisions/2026-11-22-cog-capability-neutral-upgrade.md and
  Cookpit/docs/COG_UPGRADE_ACCEPTED_SCOPE_20261122.md (G3 and G6).
  It requires independently qualified host capabilities, effect policy,
  current authority and outcome proof. No general write dispatch,
  autonomous financial execution or admitted learning is claimed here.

Do not conflate local workspace command acceptance with admission of the
native cognitive faculty. Preserve the approved conversation UI and report
actual capability status.
