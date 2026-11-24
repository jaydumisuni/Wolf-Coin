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
Linux deb: 52487c6636573ee20f7c8b6ab27d82eba22d2837355dfd25e4ef18a046a431f0
Windows ZIP: 979b57d9956df66c52738cb4d2d6ea765b5ce5cb9310880ae2a058f8bb691f14
Android debug APK: c770b78416f95ef2bae0a3afcf96e7eacb2affe3bdc122e5f642d16296790979
Nine-screen visual archive: e6fef9a98b63ef8a488596a57ad31b06f48466dc9d82ec0898b090eb52bbe7c4
