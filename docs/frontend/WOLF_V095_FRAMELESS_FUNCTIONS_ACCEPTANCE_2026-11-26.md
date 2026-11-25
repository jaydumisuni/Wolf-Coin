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
