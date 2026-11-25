# Wolf-Coin v0.9.5 — frameless desktop chrome and functional controls

Date: 2026-11-26
Branch: work/wolf-order-entry-session-20261125
Original baseline: v0.9.4-dev2, source at 5b18a61.

## Change authority

Owner requests no separate black Windows/Linux operating-system title bar
with a duplicated "Wolf-Coin ..."-style title. The existing Wolf header
is authoritative; put native minimize, maximize/restore and close buttons
by Notifications. Browser tab strip shows them when Browser uses full-height
mode. Preserve nine screen routes, browser control and existing accounts.

## Implementation

- Windows/Linux Electron main BrowserWindow is frameless; macOS remains
  native-framed and is explicitly out of scope of current physical build.
- Electron main-process authenticated IPC owns actual OS minimize,
  maximize/restore, close, state and change events.
- Browser tab strip and regular header each show native title controls
  exactly when the host supports them. Buttons are no-drag regions inside
  Electron draggable chrome. No extra title strip or duplicated page bar.
- Startup toggle writes native Windows login item or XDG Linux user autostart;
  startup status is read back from host. QA uses isolated startup directory;
  QA will not mutate Windows startup registration.
- Automatic account refresh now schedules native browser observation;
  monitoring option schedules native backend multi-account synchronization,
  excluding explicitly paused accounts. Configurable 15/30/60/300-second
  intervals. Background preference allows refresh while application is
  minimized, without claiming to run after process exit.
- In-app notification toggle affects normal status messages but critical
  warnings and errors continue.
- Session pause/resume now records PAUSED / OFFLINE in the signed native
  backend rather than changing only the UI label. Explicit paused IDs
  guard both the active-webpage observer and the cross-platform observer
  against stale automation races. Resuming requires fresh readback and
  does not assume successful provider login.
- Native device status is queried from browser host, backend and OS vault.
- Nonoperational app-lock, biometric and generic encryption toggles were
  removed, rather than pretending those features are enabled. OS-encrypted
  credential vault and isolated browser profiles remain real separate
  mechanisms. These protections do NOT imply app-wide encryption, biometrics
  or OS lock-screen enforcement.
- Reset Workspace Layout now resets only layout/presentation; does not
  delete registered accounts, cookies, credentials, activity or backend
  records. Existing owner backend and D-XQT runtime preserved.
- Source/standalone preview text now distinguishes native capabilities.

## Evidence from native Linux controlled fixtures

- WOLF_NATIVE_FRAMELESS_WINDOW_CONTROLS_PASS, tested under a genuine
  Xfce window manager on separate Xvfb display. Normal header three
  controls next to Notifications, Browser tab strip three controls and bell,
  maximize/restore, minimize, no duplicate topbar, all passed.
- WOLF_NATIVE_FUNCTIONAL_CONTROLS_PASS: toggling OS startup on/off with
  isolated XDG autostart file; autosync and automation timers on/off;
  background and notification controls; host status; fake lock/biometric/
  encrypt toggles absent; workspace reset retains records.
- WOLF_REAL_SCHEDULED_BACKEND_SESSION_PASS: 15s timer moved signed backend
  observation count 2 -> 7, then PAUSED and OFFLINE transitions were
  verified in signed backend and stored website login retained.
- WOLF_ALL_VISIBLE_ACTIONS_DISPATCH_AUDIT_PASS: 64 unique visible action
  names across nine views, eight Settings sections, six Security sections
  and five Browser panels; zero unmatched native/renderer handler names.
  This proves dispatcher coverage, not third-party integration execution.
- WOLF_NATIVE_UI_E2E_PASS: all nine views, fixture login, balance K750,
  pending K100, P&L K60, DOM, network, screenshot, scroll, logout and
  account registration retention.
- WOLF_COMPACT_BROWSER_UI_E2E_PASS: 47 currencies, collapsed sidebar and
  browser utilities geometry, manual preference, no duplicate browser bar.
- WOLF_LINUX_DPKG_INSTALL_LAUNCH_REMOVE_PASS on v0.9.5~dev1 after updating
  the login-required test to accept the signed backend's initial LOGGED_OUT
  or UNVERIFIED state. World-readable installed resources, native site
  fixture and signed financial audit are verified in fakeroot root.
- Android v0.9.5 debug QA built and installed on API35 emulator, version
  code 17, SHA-256 762cf62cb2749d3f43dd4eb8096b173945053e7005621dd84790b4a305aa0832.
  Installed APK readback matches input; 9 screens, D-XQT v8, signed backend,
  isolated WebViews and AndroidKeyStore vault passed. Mobile app has no
  desktop window controls and no false security switches.

## Explicit bounds

Source and installer tests do not imply independent acceptance of real
money movement, every third-party provider's login or transaction, a
production-signing key, physical Android device or owner pixel-perfect
visual acceptance. Backend decision/action authority remains the owner's.
The Android QA package uses com.thetechguy.wolfcoin.qa and does not alter
the standard Android app. D-XQT runtime stays owner-held in local compiled
assets, never GitHub source.

## ATHENA Windows installed acceptance — 2026-11-26

The tested portable v0.9.5-dev application was assembled locally on ATHENA
using the owner-held private D-XQT runtime recovered from the earlier
installed app HTML, with cloned Git source commit 3f0a194. Never checked
private D-XQT or compiled app HTML into public source.

Controlled Windows QA with isolated login/backend data passed:
- WOLF_NATIVE_FRAMELESS_WINDOW_CONTROLS_PASS (same native-window-controls
  test used on Linux): three genuine OS controls next to notification bell
  in each relevant header, no duplicate browser top bar, maximize/restore,
  minimize. Verified Win32 client-to-screen top inset = 0px in the new
  frameless QA app; previous installed app inset had been 30px.
- WOLF_NATIVE_UI_E2E_PASS (9/9 tabs, website actions, session login,
  screenshot, DOM/network and signed K750/K100/K60 candidate values).
- WOLF_NATIVE_FINANCIAL_ACTIVITY_UI_PASS (one signed backend account,
  five observations, thirteen audit events and clickable Activity detail).
- WOLF_ALL_VISIBLE_ACTIONS_DISPATCH_AUDIT_PASS (65 visible action names,
  zero missing dispatcher names across all 9 pages, 8 Settings sections,
  6 Security sections and 5 browser utility panels).
- WOLF_ORDER_ENTRY_E2E_PASS (Bet and Trade entry points open correct
  registered provider profiles, preserve account isolation).
- WOLF_CLEAR_ALL_NATIVE_SESSIONS_PASS (two test logins cleared; registered
  accounts and last-known K750 balances preserved).
All were controlled fixtures; no real money moved.

The installed ATHENA v0.9.4-dev2 user app was gracefully closed and
reopened from the same installed executable with v0.9.5-dev resources.
Its original account/profile directory under AppData/Roaming was not
modified. The five previous application resources were backed up under:
AppData/Local/Programs/Wolf-Coin/resources/
app-backup-v094-before-v095-20261126
(including SHA256-MANIFEST.json). Live process was observed running and
Win32 client-area top inset read 0px after update. The installed app
HTML SHA256 was:
c95bc51b0185c9d152f079822dd6ba864edff5f8790b4b2c31dd394c2958438b

Builder audit, on ATHENA using installed THETECHGUY Software Builder:
- The first isolated build correctly rejected the packaged candidate at
  runtime because the stage lacked wolf_vault.cjs. Recovered that source
  module along with current backend runtime modules.
- Second run passed Electron source readiness, native NSIS build, runtime
  module staging and Builder runtime smoke (main-window title observed).
  The standard unsigned NSIS setup is archived in Builder's private area:
  D:/projects/THETECHGUY Software Builder/builder_artifacts/
  Wolf-Coin/v0.9.5-dev/Wolf-Coin Setup 0.9.5-dev.exe
  SHA256 bd71bc48641a0f02152c800c1d34050d0434d626a88f96f150ea6a01ba311611
- Builder's additional custom graphical-installer wrapper failed a
  required free-disk preflight: 1.51 GiB required on project drive C:,
  only approximately 0.67 GiB available. No unrelated project or older
  Builder artifacts were deleted to bypass this gate. This is NOT a
  qualified graphical-wrapper release and is not represented as one.
- After copying the NSIS and Builder reports to its private artifact
  area, only disposable v0.9.5 test profiles, duplicated QA portable and
  newly created staging dist were cleaned. The user's original app,
  current user data, other Builder source and prior build outputs remain.

Android acceptance on API35 QA emulator:
- com.thetechguy.wolfcoin.qa v0.9.5-dev, versionCode 17, installed
  and readback package hash matched artifact.
- SHA256 762cf62cb2749d3f43dd4eb8096b173945053e7005621dd84790b4a305aa0832
- Nine views, D-XQT v8, signed backend, isolated WebView profiles,
  AndroidKeyStore credential-vault availability and zero fake desktop
  window controls. The standard Android package was untouched.
- Physical-device qualification and original Android signing-key
  continuity remain independent.

Private local release artifacts (NOT GitHub source or public release):
- KRATOS: /home/kratos/projects/Wolf-Coin/.workspace/releases/wolf-v0.9.5-dev1
  (Debian + Android QA and SHA256SUMS).
- ATHENA: existing Builder artifact folder above (NSIS and smoke reports).

## Contribution classification

Update existing documentation. The v0.9.5 implementation and controlled
cross-platform proofs are new relative to v0.9.4. Owner final visual
sign-off has not been obtained. Native app lock / biometric auth /
application-wide encryption remain unimplemented, with false toggles
removed rather than claiming enforcement. Runtime handler coverage is
not a guarantee of third-party provider execution, current account login,
physical device qualification or independent production acceptance.
