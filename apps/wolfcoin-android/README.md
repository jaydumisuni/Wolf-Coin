# Wolf-Coin Android v0.8.0 — WebView native application

Wolf-Coin Android packages the nine-screen D-XQT frontend and an AndroidX
WebKit-based Wolf Browser. Each account has its own persistent named WebView
profile with isolated cookies and storage. Standard website controls are
supported within the selected account's authenticated browsing session.
The browser does not install product-category button restrictions.

Tested on KRATOS's real Android 15 x86_64 emulator: APK installation and
SHA-256 readback, real Activity/WebView launch, D-XQT startup, all nine
screens, two independently authenticated accounts, account-holder matching,
portfolio comparison, app restart and cookie/profile isolation. Profile
cookies are flushed after page navigation and when the app stops.

Build from the native Android Gradle project; its generated wolfcoin.html
and the owner-held D-XQT binary are kept out of the public source branch.
This APK is debug-signed, not production distribution-signed.

The 0.1.0a10 signed Python/SQLite native backend is integrated into
Windows/Linux Electron, not yet embedded into this Android APK. Android
production backend parity, third-party platform compatibility and physical
Android-device acceptance remain separate tasks.


Website camera/microphone/media permission requests use a normal website
permission dialog and Android runtime permission prompts. They are not
silently rejected by a hardcoded category rule. A physically connected
phone is still required to qualify actual capture-device permission behavior.
