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
