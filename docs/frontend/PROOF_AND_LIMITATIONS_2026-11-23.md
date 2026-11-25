# Wolf-Coin Frontend v0.6 — KRATOS Proof and Boundaries

2026-11-23, development candidate. No MT5, sportsbook API, live account, funding or financial transaction was used.

Observed passes on KRATOS:
- Electron 37.2.6, isolated Chromium fixture sessions.
- Fixture login, logout, screenshot, DOM inventory and read-only network metadata.
- Heuristic ZMW 750 balance, 100 pending and +60 P/L from controlled fixture, marked candidate_only.
- Persistent cookie restored after full Electron restart; explicit session clear forced login. Session-only cookies must not be artificially extended.
- Real UI/CDP Add Platform -> login -> Inspect & Sync -> Log Out retained registered account and last-known balance.
- Linux .deb built (SHA256 25097ce141bd52c0245d1acfc31594aaec15ae4ee6dc53e54f1d6ba26f5877f5).
- Windows x64 portable ZIP built (SHA256 816849323cf8eaedd9e7513b704d0bdae2a03d2d557b1d576346c688ddfbadb1).
- Android debug APK compiled with SDK35, JDK21, Gradle8.7, AGP8.5.2, WebKit1.13.0 (SHA256 483b8093b4a1e3861f64d22e0ff4274156e9c6d4aa4e8da9fc7489a908dd16df).

Not proven: physical Android login/profile tests, Windows runtime tests while ATHENA offline, installed Linux setuid sandbox acceptance, exact pixel-level owner-approved nine-tab match, provider OAuth compatibility, background monitoring, financial reconciliation, backend ingestion and live accounts.

The browser controller exposes account-scoped website controls. The separately developed backend governs its own decisions and reconciliation. Testing used controlled fixtures.

## Follow-up verification: Browser Tools / native empty-state

- Native boot initialized with zero registered demo accounts and zero claimed live financial values.
- Full real UI fixture path passed again on KRATOS with embedded D-XQT ready.
- Account-specific Browser Tools now call their actual host functions: read-only page snapshot, DOM inventory, request metadata, native screenshot and bounded guided scroll action.
- Browser panel is temporarily concealed during UI modals while the underlying authenticated page and account session remain alive.
- Rebuilds use an owner-held private D-XQT payload via apps/wolfcoin-ui/assemble.py. Never commit the generated app.html, Android wolfcoin.html or private runtime to the public source branch.
- Android modal overlay behavior was adjusted to keep the underlying WebView layout/viewport intact. Android physical runtime remains a separate acceptance gate.

## Final expanded native UI check
A repeatable Node/CDP fixture test (apps/wolfcoin-desktop/tests/native_ui_e2e.mjs) passed on KRATOS with no startup demo accounts, all nine visible tab render paths, Add Platform, native login, Inspect & Sync, page snapshot, DOM controls, request metadata, screenshot, guided scroll, and Log Out retaining last-known values. Source and binary package consistency were also checked across Linux .deb, Windows ZIP and Android APK. No claim of Android hardware or Windows runtime acceptance follows from these tests.


## Native package acceptance checkpoint (2026-11-24)

The actual finalized Linux .deb, after Debian extraction, passed the same native_ui_e2e.mjs flow as the source build: native start with zero fake accounts, 9/9 tabs, platform addition, authenticated fixture navigation, DOM snapshot and candidate ZMW reconciliation, network metadata, screenshot, guided scroll, logout retention. This confirms exact package bytes, not only development source. It ran in an isolated test X server with the development --no-sandbox flag because an extracted rather than system-installed package cannot have an effective root-owned sandbox helper. The .deb itself contains the root-owned setuid helper and world-readable app contents, but installed sandbox acceptance remains open.

All three distributables were checked for exact embedded frontend-byte equivalence to their assembled source: Linux .deb and Windows ZIP use the desktop HTML, Android APK uses the Android-specific HTML with its same-origin host bridge.

Release remains an owner-only draft integration candidate. It is not a production or real-money acceptance, nor evidence of Windows/Android runtime tests.

## v0.8.0 integration acceptance (2026-11-24)

- Native Electron + signed 0.1.0a10 application backend: two currency-separated
  accounts, HMAC operations, history, restart and audit passed on KRATOS.
- Real native UI Add Platform, controlled login, Inspect & Sync, five browser
  tools and logout passed on the integrated Linux package. Actual SQLite
  readback: one account, five observations, thirteen audit events, logged-out
  account retained. No backend errors in the passing fixture run.
- Finance, Activity, Overview, balance history, reports and CSV use backend
  records instead of invented demo financial transactions in the desktop app.
- Two separately authenticated platform sessions, owner match, linked portfolio,
  quote comparison 2.1 vs 2.3 and queued candidate persistence passed in
  the integrated desktop UI. Native Sync All refreshed both websites and
  wrote both backends' account history without selecting their visible tabs.
- Generic market DOM discovery of ordinary data-odds controls passed with
  Home 2.10 and Draw 3.15. Provider-specific websites remain unqualified.
- Linux .deb and Windows portable ZIP content and SHA passed. The exact
  extracted Linux package also passed full browser/backend UI testing under
  a development X server. Windows launch on ATHENA remains unverified.
  Desktop native backend uses a Python 3.11+ runtime; Windows portable ZIP
  does not include an embedded interpreter yet.
- Android 15 emulator installed the v0.8 debug APK and verified package
  readback, nine screens, D-XQT and independent profiles. Two logins, portfolio
  comparison, restart account state, original cookie restoration and an
  independently isolated new profile passed after the WebView flush fix.
  Android native backend IPC is not integrated in this APK yet.
- All nine actual UI screens captured at 1440x900 for visual inspection.
  Pixel-exact match with the user's selected mockups has not been independently
  approved. No live external platform login or financial operation was tested.

Verified SHA-256:
Linux deb: 9a5feaf4a69c3394fd97bba950ac0c1c8121e9e9cc0ef114efe7e54f381c6e95
Windows ZIP: da611de62ab7bcce32353119395b059f9758083d4215a05cc91f936cbe6d01c0
Android debug APK: ec39e064267f6fdec7e86cc16337806a4f3664b600617722d655f0d504bf86db
Nine-screen visual archive: e6fef9a98b63ef8a488596a57ad31b06f48466dc9d82ec0898b090eb52bbe7c4


## Android browser website permissions (v0.8 final build)

Removed a legacy WebChromeClient blanket permission denial. Websites now
display Android's normal owner-visible permission prompt, with Android
camera/microphone runtime permission requests when appropriate. No website
permission is silently granted. The owner chooses at the OS prompt.
The Android 15 emulator verified compile/install and all native WebView
readbacks after this change. Media-permission hardware behavior on a physical
phone remains unqualified.


## Additional final v0.8 integration readbacks — 2026-11-24

- The owner-held signed backend returned BROWSER_HANDOFF_READY from a synthetic
  contextual proposal and accepted a NOT_EXECUTED native receipt; no external
  website action or actual financial effect took place. Source test:
  apps/wolfcoin-desktop/tests/backend-integration.e2e.cjs.
- Generic visible-site classification was tested against the public betPawa
  Zambia landing page, identifying its betting category from title/headings.
  No markets or quotes were exposed in the inspected public DOM; none were
  invented. This demonstrates public landing-page category discovery, not
  provider-specific betting market acceptance.
- Android WebView now implements child/popup windows using the account's
  existing named WebView profile. A controlled OAuth-style popup login
  completed and the parent WebView recognized the restored authenticated
  account; a different account's profile remains separate. This does not
  establish actual provider OAuth acceptance.
- Android request-metadata observation no longer skips whole requests by
  arbitrary URL path keywords; bounded/opaque path segment representation
  remains in the metadata feed.
- The final APK (SHA above) passed installed-APK hash readback, actual WebView,
  embedded D-XQT, nine tabs and popup account authentication.
- Final Linux package was extracted and passed the nine-tab/native backend
  Chromium acceptance test, including logout state convergence and backend
  SQLite readback. The logout test polls for both the native backend state and
  visible UI rather than assuming an arbitrary 500 ms completion deadline.
- All final Windows/Linux/Android package application bytes match assembled
  sources. Windows runtime qualification, Linux system-installed sandbox,
  Android embedded backend parity, actual external authenticated providers,
  and mockup pixel-match approval remain open.

## Android source-built v0.9 native backend acceptance, 2026-11-24

The exact native Android source project built the Chaquopy Python3.11
application backend, Kotlin WebKit host, nine-screen D-XQT UI and signed
wolf.app.bridge.v2 host connection. Native Android 15 x86_64 emulator proof:
- Direct installed APK SHA-256 matched the exact source-built APK.
- Trusted WebView host returned a genuine embedded Python backend and
  22 supported bridge operations; D-XQT and all nine tabs ready.
- Browser-originated K750 fixture observation stored in Android SQLite,
  native financial history and audit readbacks passed, and Overview,
  Finance and Activity screens showed actual backend records.
- Synthetic decision yielded BROWSER_HANDOFF_READY and test receipt
  NOT_EXECUTED. No real financial transaction was performed.
- On process restart, account persisted, state began PAUSED/STALE_LAST_KNOWN,
  browser cookie restored, new observation revalidated ACTIVE and history
  accumulated.
- Two independently authenticated fixture website origins each created
  native backend financial histories; Android Sync All returned two
  OBSERVED results, and owner-match suggestions were available.

APK versionCode11, versionName0.9.0-dev, minSdk26 and targetSdk35.
SHA-256:
37e71b7c3012ef9a0db5a0400d46b5254ab0b365f2d734b06d746a544c8612c9

Remaining: Windows launch on ATHENA, Debian installed sandbox, physical
Android acceptance, exact owner-approved visual mockup parity, production
signing and real authenticated third-party venue end-to-end acceptance.

## 2026-11-25 visual and game-safe Windows acceptance review

Recovered the approved/reference Wolf-Coin concepts in the user's file library and
compared them against all nine genuine 1440x900 screenshots in the earlier
v0.8 draft release visual-evidence ZIP. This is a visual review, not an
owner-signed pixel-equivalence certificate.

Observed material differences requiring correction before Gate 5:
- Overview: reference has four financial KPI cards, a paired account/session
  dashboard, richer chart and activity areas; the genuine v0.8 native screen
  has registered-account/session/currency counts, a larger balance-history
  panel and an audit-oriented activity list. Actual backend facts must remain
  truthful; missing financial data must not be filled with fabricated values.
- Accounts: dark wolf identity and blue active-navigation style are present,
  but account-card proportions, table density, typography and artwork
  placement differ from the reference.
- Browser: live controlled fixture login displays correctly, but the
  surrounding tabs/navigation/header spacing and branded start-page framing
  do not reproduce the selected conceptual browser composition exactly.
- Financial Data / Activity: actual backend records replace illustrative
  concept transactions; lists are substantially less decorated and the
  reference's dense, multicolored ledger/chart treatment is not yet matched.
- Sessions / Platforms / Settings / Security: all pages render, but the
  reference uses larger sections, higher contrast, more prominent status
  graphics and more carefully distributed cards. Empty states are genuine.

Windows acceptance preparation (no user desktop activation):
- ATHENA was reachable by Oracle terminal, and Call of Duty was running in
  the foreground. No visible application windows, focus switches, keyboard,
  pointer operations, game restarts or priority changes were performed.
- Node.js 24.19 and Python 3.14 were found on the machine.
- Added opt-in WOLF_BACKGROUND_QA=1, usable only with WOLF_TEST_MODE=1,
  creating an invisible/unfocusable taskbar-free Electron QA window with
  hardware acceleration disabled in that test configuration.
- Added windows-background-acceptance.ps1 with explicit package marker
  verification, independent fixture profile, low-priority child processes,
  expected native fresh/restore proof markers and foreground PID continuity.
- PowerShell parser and Node syntax checks passed on ATHENA; terminal-only
  preflight returned game_active=true, foreground_pid=24304,
  package_ready=false, decision=preflight-only. The released Windows ZIP was
  not yet locally staged; a full Windows runtime test was therefore NOT run.
- KRATOS workstation control was refused by Oracle (AI Takeover OFF), so
  no new KRATOS/UI package build or production installation was attempted.

Gate 5 remains unaccepted due visible design differences; Gate 6 still needs
actual hidden Windows package execution and a physical Android confirmation;
Gate 7 production installers/signing and system-installed Linux sandbox remain
open; Gate 8 requires owner-authorized real-provider end-to-end proof.
The most recent acceptance table lists eight gates; no authoritative Gate 9
was found in that table, and an unrelated older Phase 9 must not be conflated.


## Windows ATHENA invisible runtime acceptance — 2026-11-25

ATHENA's original owner-only draft Windows ZIP was transferred using Windows
BITS Low priority while Call of Duty remained in the foreground. Its complete
139703784-byte SHA-256 matched the previously frozen package digest
da611de62ab7bcce32353119395b059f9758083d4215a05cc91f936cbe6d01c0.
An isolated copy was extracted, and only the frontend main.cjs was patched
from the source branch to enable WOLF_BACKGROUND_QA.

The invisible QA Electron launch (show=false, focusable=false,
skipTaskbar=true, disableHardwareAcceleration in test mode) passed:
- WOLF_NATIVE_FIXTURE_PASS with authenticated DOM observations K750 / K100
  pending / K60 P/L, native account/profile isolation and website controls.
- WOLF_NATIVE_RESTART_AND_REMOVE_PASS with persisted authenticated session
  across restart and confirmed removal.
- Node.js and Python 3.14 were installed on ATHENA.
- The same foreground Call of Duty process, PID 24304, remained active and
  retained the foreground window throughout both stages.
- Windows PowerShell's Start-Process wrapper returned a null (unavailable)
  managed ExitCode even though WaitForExit succeeded; the first test wrapper
  incorrectly treated null as failure. That harness defect is corrected:
  a non-null nonzero exit code fails, and every stage additionally requires
  its explicit in-application PASS marker and completed process. No zero exit
  code is asserted where the host did not return one.
- A gratuitous remote-debugging port flag was removed from invisible QA;
  it had caused a harmless DevToolsActivePort write error under the temp path.

This passes an offscreen functional Windows integration check for the
isolated portable package. It does not certify a system-installed Windows
release, production signature, pixel-exact UI, or any real sportsbook account.

## v0.9.1 combined-frontend and Windows packaging acceptance, 2026-11-25

Updated the actual backend-connected nine-screen Overview to the four financial
KPI cards and a paired Account Summary / Session Health / Quick Actions layout
closer to the owner-selected mockup. The lower row now contains backend-derived
balance history, audited activity and financial/backend health. The numbers
come from current native backend observation records and are not fabricated.
When currencies differ, totals explicitly remain separated instead of summing
incompatible units. The old UI Prototype title was corrected.

KRATOS rendered all nine revised native Chromium screens at 1440x900 to
private visual evidence and passed the full native UI fixture and financial
backend view tests. This is improved layout fidelity, NOT an approved
pixel-exact mockup match.

ATHENA Windows no-focus acceptance on 2026-11-25 passed two stages using an
isolated owner-only Windows portable package with the offscreen mode patch:
- fresh authenticated login / DOM balance candidate K750, pending K100 and
  P/L K60 / network telemetry and independent account sessions,
- restart with authenticated cookie persistence and explicit session removal.
The same Call of Duty process PID 24304 retained foreground ownership.
No visible Wolf-Coin window was opened. The PowerShell process ExitCode field
was unavailable (null) despite successful WaitForExit and both application
PASS markers; the harness was corrected to report that fact explicitly and
still reject any reported nonzero process status.

The Windows 0.9.1 host now selects an official, locally bundled embeddable
CPython 3.14.7 executable when available and otherwise supports the existing
host installation. The release staging procedure validates the official
Python archive SHA-256
d297e5ff019966817ad8502465176139f2d3d840fa4ed84b13bed399a6ab1f15,
keeps PSF LICENSE.txt, and configures Python's private ._pth import path
for both loose and ASAR-unpacked owner-held backend modules.
This packaged-Python build path is source-tested; runtime acceptance using
the newly bundled interpreter will be reported separately after ATHENA proof.

Other still-open qualification: physically connected Android, production
installer signing, owner approved pixel parity, and real authenticated
third-party provider lifecycle and action results. No invented Gate 9.

## v0.9.1 release candidate — 2026-11-25

The 0.9.1 development candidate was assembled from this exact frontend branch
with the owner-controlled D-XQT v8 and 0.1.0a10 backend staged locally.
No private runtime, staged backend code, signing key or live account state
is tracked in the public frontend Git branch.

**Windows, ATHENA.** The isolated portable application ran with the official
embedded CPython 3.14.7 runtime without the host Python override. Both fresh
and restart QA sessions passed using a hidden, unfocusable, low-priority
window. The signed backend returned all 22 operations and the native
browser passed fixture login, independent sessions and cookie continuity.
Call of Duty retained foreground PID 24304 throughout. This validates
the bundled interpreter/bridge and prior host renderer. The byte-identical
0.9.1 Windows ZIP itself was verified against staged source assets on
KRATOS, but the final ZIP and new NSIS setup were not interactively launched
on ATHENA while the user was gaming.

**Linux, KRATOS.** The exact final 0.9.1 .deb was extracted and its
application bytes matched the assembled source. Real Electron/Chromium under
an isolated Xvfb session passed nine-tab navigation, account add/login,
K750 balance, K100 pending, K60 P/L, five browser tools, logout/preserved
last-known data, native backend Overview/Finance/Activity and history.
Ordinary market-odds controls were extracted correctly in a separately
isolated browser instance (Home 2.1, Draw 3.15).
The market test failed when rerun inside a previously used browser test
profile but passed on a fresh profile; the authenticated website test
required waiting for the target form to finish loading. These were
recorded as test-isolation/readiness findings, not silently ignored.

**Android, KRATOS.** The exact source-built versionCode12 APK was installed
on the Android 15 x86_64 emulator. Installed APK SHA-256 matched the source
APK. The application demonstrated embedded D-XQT ready, nine native tabs,
signed CPython 3.11/SQLite financial observation K750, native audit and
contextual decision/NOT_EXECUTED receipt, two independently authenticated
fixture websites with separate persisted financial histories, native
Sync All and an observed same-owner matching suggestion. After force-stop
and restart the account recovered initially PAUSED/STALE_LAST_KNOWN, then
returned ACTIVE upon browser session cookie restoration and reobservation
with history retained.

The older lab APK and its application data were backed up before the
0.9.1 reinstall. Its debug-signing certificate differed from the current
build, so an in-place upgrade was not possible. The older lab artifacts
were preserved; the 0.9.1 signing identity is laboratory-only. Production
releases require a consistent owner-controlled signing key.

**Installers.** The release includes a full owner-controlled Windows
portable ZIP with Python 3.14.7, a Linux .deb, Android debug APK and a
per-user Windows NSIS setup executable built on KRATOS. The NSIS compiler
completed successfully twice with a reproducible executable SHA-256,
and the file is identified as a PE32 NSIS self-extracting installer.
No interactive Windows installation/uninstallation was exercised while
ATHENA's game was running. Linux system-managed installation and physical
Android qualification remain separate acceptance criteria.

**Visual review.** All nine current source screens were captured at
1440x900, and the Overview now follows the reference's four-KPI and
3-column session/quick-action structure using actual backend data.
Pixel-perfect matching and owner visual approval remain outstanding.

**Final artifact SHA-256**
- Linux .deb: a287f576030216c313c80dceea9c6dec8ec2000da13626cefd291a25dd1
- Windows portable ZIP: c63c61ef2e7ce5de8050a7192efcf752824eb3a78a3199c701f8b289f249321d
- Windows NSIS setup: 6fada8d002ed3512c7c037a7daf8e2c399dd8b0b23701058b790057ef5ef9de1
- Android debug APK: 6a11b58e7e099b06a51e5113171f6bf98cb41366ca37ac531664439b5f5f13fb
- Nine screenshots: 2aa06b0621f100a31ee38a6409657788b6341d55bfacbae99b453777fdf1d943

The user-defined gates 5–8 cannot all be marked closed until visual
approval, required physical/native install acceptance and real third-party
authenticated workflow validation are supplied. There is no authoritative
Gate 9 in the earlier eight-gate table. No new global product-mode
restrictions have been introduced.
