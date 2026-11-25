# Wolf-Coin v0.9.4 development — order entry and session ownership

Source branch: `work/wolf-order-entry-session-20261125`
Date: 2026-11-25. Implements the user's request for a visible entry point
for betting/trading and cross-platform saved/clearable website sessions.

## UI and behavior
- First-class Place Bet and Trade actions on native Overview, account
  management and compact browser toolbar. Both open a platform picker,
  market/instrument, selection/direction, optional stake/amount and the
  matching registered website in its own persistent native browser profile.
- When market/selection and positive amount are provided, the frontend can
  request a signed `wolf.app.bridge.v2` `decision.propose` operation. The
  backend context may return `CONTEXT_STEP_REQUIRED`. This is a proposal,
  not a completed external platform transaction. Real bet/trade completion
  remains on the actual platform, with platform readback required for
  reconciliation. No invented execution or new global product lock.
- Dedicated Tools sidebar action Clear this browser profile, available for
  independent `default` profile and registered accounts. Local cookies,
  website data and cache are cleared without deleting account registrations.
- Log Out All now invokes native `clearSession` for registered accounts
  before updating UI status. Android closes owned popups and active WebView
  before clearing its isolated profile. Electron closes owned popups,
  clears explicit cookie/site storage/cache categories and verifies that
  the cookie jar is empty.

## Evidence
- Linux Electron `WOLF_ORDER_ENTRY_E2E_PASS`: no-platform registration
  suggestion, actual registered betting/trading website launch, isolated
  profile routing and visible Overview/browser actions.
- Linux Electron `WOLF_NATIVE_FIXTURE_PASS` and
  `WOLF_NATIVE_RESTART_AND_REMOVE_PASS`: HTTP-only cookie persisted after a
  complete restart, second profile was still logged out, explicit clear
  returned first account to login screen.
- Linux package `wolf-coin_0.9.4~dev1_amd64.deb`: rootless fakeroot dpkg
  install, full signed backend UI/financial history E2E and uninstall
  passed (`WOLF_LINUX_DPKG_INSTALL_LAUNCH_REMOVE_PASS`).
  SHA-256:
  `779ae47621f06614ea9e1c0348c9ea205fae75392a2d057613d7eba391c9ddbf`.
- Windows portable candidate built from a verified v0.9.1 Electron
  distribution, with private D-XQT binary retained locally.
  SHA-256:
  `4fa9aa159821e7c8db7f915041651aae96b7e84b017b4ee9d8b4fdcab6961c0d`.
  Windows v0.9.4 source-identical native portable acceptance **passed** on ATHENA in an isolated user profile; see final readbacks below.
- Android 0.9.4 debug APK compiled and HTML matched source. The existing
  emulator v0.9.3 installation is signed by SHA-256 cert
  `9236d4361f1da47a120a58efb5618b0d0f250259c638cbc249f76775cc6be6ef`,
  while the current local debug keystore cert is
  `648297734fbf48cb4d3460b892e84303fbbadb6f494d086f7bd89d9b76034645`.
  An in-place upgrade was correctly refused by Android. The previous
  installation and its data were NOT erased.
- Isolated Android QA flavor with package `com.thetechguy.wolfcoin.qa`
  passed actual APK installation/hash/readback, nine-tab WebView D-XQT,
  backend UI, browser Place Bet/Trade entry points
  (`WOLF_ORDER_ENTRY_E2E_PASS`), and two-profile cookie lifecycle:
  `WOLF_ANDROID_SESSION_ISOLATION_PASS`,
  `WOLF_ANDROID_SESSION_RESTART_CLEAR_PASS`. This is an emulator, not a
  physical Android device.

## Provider-specific limitations

Google's official OAuth 2.0 policy prohibits authorization requests
inside embedded user agents (developers.google.com/identity/protocols/
oauth2/policies). A system-browser login for Google is separate from
Wolf-Coin's embedded cookie jar; it cannot be described as automatically
persisting inside Wolf. A provider-backed redirect / native OAuth
integration is necessary to share authorized results, and external
provider behavior must be qualified per service. Other ordinary website
sessions retain their isolated persistent cookies unless cleared, expired,
revoked or blocked by the website.

## Packaging/privacy
The source repository is public. Do not upload packaged private D-XQT
runtime artifacts to public releases. Generated apps/APKs with private
runtime remain on owner workstations until an owner-controlled private
distribution route is approved.

## Final cross-platform acceptance readbacks — 2026-11-25

**Windows ATHENA, v0.9.4 native executable**: Native Electron distribution
was assembled locally from the same public source branch with owner-held
D-XQT v8, matching KRATOS source and private-runtime hashes:
- `WOLF_ORDER_ENTRY_E2E_PASS`: first-class betting/trading platform launch
- `WOLF_COMPACT_BROWSER_UI_E2E_PASS`: nine tabs, collapsed sidebar,
  five browser panels, 47 selectable currencies
- `WOLF_NATIVE_UI_E2E_PASS`: full browser controls and site fixture
- `WOLF_NATIVE_FINANCIAL_ACTIVITY_UI_PASS`: signed native backend records,
  observed K750 cash, K100 pending and K60 P/L and audit detail
- `WINDOWS_V094_PERSISTENT_LOGIN_RESTART_CLEAR_PASS`: persisted HTTP-only
  cookie through app restart, independent second account profile, explicit
  session clearing returned site to login page
- `WOLF_CLEAR_ALL_NATIVE_SESSIONS_PASS`: two genuine isolated logged-in
  Chromium profiles both cleared via UI while last-known account records
  and balances were preserved.

**Linux KRATOS**: v0.9.4 final .deb rebuilt after OAuth fallback addition,
installed with isolated fakeroot/dpkg database, executed signed native UI
and backend acceptance and removed without changing host package database;
`WOLF_LINUX_DPKG_INSTALL_LAUNCH_REMOVE_PASS`.
Additional `WOLF_CLEAR_ALL_NATIVE_SESSIONS_PASS` on independent fixture
profiles. Acceptance script now refuses occupied CDP ports, supports caller
selected test ports and terminates the full QA process group at exit.

**Android emulator**: v0.9.4 isolated QA package
`com.thetechguy.wolfcoin.qa` installed and hash-verified with nine WebView
tabs, genuine D-XQT and backend. Entry point,
`WOLF_ORDER_ENTRY_E2E_PASS`; two-profile independent cookie persistence
after process restart, `WOLF_ANDROID_SESSION_RESTART_CLEAR_PASS`;
and in-UI clear-all with account records retained,
`WOLF_CLEAR_ALL_NATIVE_SESSIONS_PASS`.
The existing original `com.thetechguy.wolfcoin` installation is untouched.
Both QA and standard debug APKs contain the same regenerated HTML and
private runtime; the standard package was compiled, not upgraded over the
existing differently signed original.

**Final immutable package hashes after Google/system-browser addition:**

| Artifact (private, local only) | SHA-256 |
| --- | --- |
| `wolf-coin_0.9.4~dev1_amd64.deb` | `779ae47621f06614ea9e1c0348c9ea205fae75392a2d057613d7eba391c9ddbf` |
| `Wolf-Coin_Windows_x64_v0.9.4-dev_portable.zip` | `4fa9aa159821e7c8db7f915041651aae96b7e84b017b4ee9d8b4fdcab6961c0d` |
| `Wolf-Coin_Android_v0.9.4-QA.apk` | `c295640d0c2dbdf3820a31aa7510992a01bc4e98a559fe1d8e3adfaa522366e6` |
| `Wolf-Coin_Android_v0.9.4-dev-debug.apk` | `f2d1836199f7c845881d6a73eb1440d70034519b7934c71294668a264b4e69a0` |

**Google Sign-In and external identity:** Official Google OAuth policy
prohibits OAuth authorization requests in embedded app-controlled
user-agents, and Google Account Help lists embedded browsers as a cause
of blocked sign-in:
- https://developers.google.com/identity/protocols/oauth2/policies
- https://support.google.com/accounts/answer/7675428

Wolf Browser Tools now exposes **Open in system browser** for a login
that requires Chrome/Brave/another supported browser. This is an
explicit owner action; its signed-in session and cookies belong to the
system browser, **not** Wolf's isolated browser profile. Clearing a
Wolf profile cannot clear an external browser's Google cookies. A
provider-approved OAuth registered-client + redirect/token architecture
would be required for authorization and account linking inside Wolf;
no bypass or cookie copying is implemented.

**Outstanding separate release gates:** production-signed Windows NSIS
installer, standard Linux system-managed apt upgrade (rootless package
transaction proven), physical Android device, signing-key continuity
for upgrade of installed Android original, provider-specific Google
authorization flow, and authenticated real financial-provider order
receipt/readback. Real-money placement was not claimed, and no external
transaction was executed by these QA workflows. The source repository is
PUBLIC and the private D-XQT-bearing package artifacts must not be
published there.

## Installed application closure — 2026-11-25

**KRATOS Ubuntu 26.04:** The v0.9.4 Debian package was installed
into the real host package database with `sudo dpkg -i`, version
`0.9.4~dev1` read back, desktop entry present. First launch revealed
a packaging mode defect: `wolf_vault.cjs` and the desktop file shipped
as 0600, so a normal user could not load the app. The two files were
corrected to 0644 in the package stage; rebuilt package SHA-256 is the
updated value above. Reinstallation succeeded. A normal-user launch
from `/opt/wolf-coin/wolf-coin` and genuine Chromium/Electron end-to-end
tests passed native browser, signed backend financial UI, Place Bet/Trade
and Clear All on two profile-isolated fixture logins. A static world-read
resource gate has been added to the rootless package acceptance test.

**ATHENA Windows 11:** The installed Wolf-Coin app's native resources
were upgraded from v0.9.1-dev to v0.9.4-dev, with the original
`resources/app` preserved as
`resources/app-pre-v094-20261125`. The Electron executable itself was
retained. `%APPDATA%/wolfcoin-desktop-host` and user cookies/accounts
were **not modified** by the deployment; acceptance ran with a separate
QA user-data path. Readback from the actually installed executable
passed all nine UI tabs, native financial/backend history, Place Bet/Trade
routing, two-account session clearing and data preservation. This is a
working in-place *development app resource upgrade*, not a production
code-signed NSIS installer.

**Android:** Two verified emulator packages remain intact. The original
application cannot receive the new debug APK because the certificate
changed; v0.9.4 QA uses a side-by-side package name. No physical Android
phone was connected during these tests, and no real Google OAuth client
registration or live provider financial transaction was validated.

## Installed Linux re-verification — 2026-11-26

Performed against the actual system-installed executable under
/opt/wolf-coin/wolf-coin, not a package extraction. All tests used isolated
Xvfb/Chromium user-data, backend paths and controlled local fixtures.

- WOLF_NATIVE_UI_E2E_PASS: D-XQT, 9/9 screens, account registration,
  K750/K100/K60 fixture, DOM/network/screenshot/actions and logout.
- WOLF_ORDER_ENTRY_E2E_PASS: visible Place Bet and Trade from Overview,
  Accounts and Browser, each opening its own registered website/profile.
  No real financial order was submitted.
- WOLF_CLEAR_ALL_NATIVE_SESSIONS_PASS: two independently authenticated
  fixture website profiles cleared, while account registrations and
  last-known K750 balances remained.
- WOLF_NATIVE_FINANCIAL_ACTIVITY_UI_PASS: fresh independent backend
  fixture, one account, five observations and thirteen signed audit
  entries with clickable detail and financial views.
  Reusing the earlier two-account clearing fixture had produced an
  expected 3 != 1 assertion; the isolated clean-profile rerun passed.
- Archived and cached Debian SHA-256:
  779ae47621f06614ea9e1c0348c9ea205fae75392a2d057613d7eba391c9ddbf
  The package version reads 0.9.4~dev1 and dpkg reports installed.
  An alternative user-provided SHA-256:
  a297a6075afd9998ff2dfe34a317535ff877436751530890405ef2518ac4f4e9
  was not found among local package candidates. These are distinct
  reported hashes, NOT verified as the same package.

Google / OAuth remains provider-specific. Official Google OAuth policy
disallows authorization in embedded user agents, including WebViews
under application control. Wolf can hand off to the system browser,
but its external session and cookies are not in Wolf's account profile
and cannot be cleared using Wolf's local-session controls. Approved
provider-native OAuth client registration, redirect/consent and token
integration remain independent work:
https://developers.google.com/identity/protocols/oauth2/policies
https://developers.google.com/identity/protocols/oauth2/native-app

Production-signed Windows installer, original Android signing-key
continuity, physical Android hardware and real third-party broker/
sportsbook financial order readback are not certified by these tests.
