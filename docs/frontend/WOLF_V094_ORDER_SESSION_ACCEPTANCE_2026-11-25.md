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
  `a297a6075afd9998ff2dfe34a317535ff877436751530890405ef2518ac4f4e9`.
- Windows portable candidate built from a verified v0.9.1 Electron
  distribution, with private D-XQT binary retained locally.
  SHA-256:
  `7299a65639071b243d9f5a6579a805af8e40efd6ed284198f57b00c29959beef`.
  Windows v0.9.4 native acceptance is a separate step.
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
