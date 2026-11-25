# Wolf-Coin 0.9.3 UI acceptance — 2026-11-25

Branch: work/wolf-browser-layout-v093-20261125.

Scope: existing nine-tab UI and native browser integrations.

## Delivered
- Removed duplicate browser title/action header and top-right menu/profile dropdown.
- Compact browser tab/navigation/address strip.
- Main navigation arrow toggles full sidebar and 66px icon rail.
- Collapsible browser utilities panel: History, Bookmarks, Tools, Passwords, Downloads.
- Time-zone based initial currency suggestion, 47 options, manual override, per-account currency preserved.
- Native backend transaction and audit entries are selectable, with recorded detail fields.
- Desktop OS-encrypted saved logins and Android Keystore AES-GCM saved logins.
- Exact-origin autofill, never automatic form submission.
- Android browser viewport does not overlap the bottom navigation.

## Recorded checks
- Electron E2E: 9/9 views, website login, synchronization, DOM, screenshot, network, scroll, logout PASS.
- Signed backend UI: clickable transaction/audit event detail PASS.
- Desktop browser geometry at 1540x1024: 1301px full navigation, 1474px compact, 1164px compact + tools, height 930px PASS.
- Currency: Africa/Lusaka suggested ZMW; manual EUR selectable from 47 values PASS.
- Desktop vault contract unit tests: encrypted at rest, exact origin, no automatic form submit PASS.
- Android 0.9.3 debug build and emulator launch, 9 views, native backend and isolated WebView profiles PASS.
- Android Keystore saved login, autofill, cross-origin isolation, app restart persistence and deletion PASS.
- Android 412x732 layout: website and sidebar end at y=660, navigation begins y=660 PASS.
- Final Android APK SHA-256: a8779bb356a2beddad4df300a8579724deedcbd2dda9570bd69765e006e1d0c5.
- No live financial execution was used in testing.

## Remaining qualification
Windows native runtime, actual Linux or Windows OS password-store integration, physical Android hardware, and owner visual approval are separate acceptance checks. The Android downloads panel is a stub; the Electron download history is connected. Existing backend is not replaced.

Private D-XQT runtime is injected during local assembly, not committed.
