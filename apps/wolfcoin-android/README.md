# Wolf-Coin Android v0.9.0-dev — embedded native application backend

The Android APK includes the nine-screen D-XQT frontend, native AndroidX
WebKit Wolf Browser with independently named account profiles, and the
existing Wolf-Coin 0.1.0a10 Python 3.11/SQLite backend. It does not need a
backend web server, Docker container or sportsbook API for offline testing.

The Kotlin host initializes Chaquopy 17.2.0 and uses an Android-private key
to authenticate the same wolf.app.request.v1 / wolf.app.bridge.v2 protocol
implemented by the native desktop application. The trusted appassets UI
receives the account-scoped wolfBackend interface; external website WebViews
do not receive the signed backend interface or host key.

## Reproducible owner-controlled build

First stage the authoritative private backend source:

  python3 apps/wolfcoin-android/stage-native-backend.py --source /path/to/a10

The eight copied modules under app/src/main/python/wolf_app and wolf_core
are Git-ignored, not part of the public frontend branch. Then assemble the
private D-XQT runtime using apps/wolfcoin-ui/assemble.py with --dxqt-js and
--android parameters. The generated wolfcoin.html is also Git-ignored.

Build prerequisites: JDK17, Android SDK35, Gradle8.7, AGP8.5.2,
Chaquopy17.2.0, WebKit1.13.0 and Python3.11 on the builder. Set
WOLF_BUILD_PYTHON to choose the Python3.11 executable. Build with
gradle --no-daemon :app:assembleDebug. APK native ABIs include x86_64 and
arm64-v8a. This is debug signing, not a production-distribution signature.

## KRATOS Android 15 emulator acceptance, November 24 2026

- Exact source APK installed with package SHA-256 matching on-device readback.
- Real Android WebView nine-screen UI and D-XQT runtime initialized.
- Embedded native signed Python backend replied to bridge capabilities.
- Browser captured K750 financial fixture observation, signed backend stored
  it in SQLite, and native Overview/Finance/Activity displayed real records.
- Backend contextual decision yielded BROWSER_HANDOFF_READY and the synthetic
  NOT_EXECUTED receipt, without a real website financial effect.
- After process restart, native account and history persisted as
  PAUSED/STALE_LAST_KNOWN, the authenticated profile cookie was restored and
  a fresh observation revalidated the account ACTIVE.
- Two distinct locally authenticated fixture websites synchronized separately
  using wolfBackend.syncAll and accumulated independent SQLite histories.
  Owner-matching suggestions remained evidential, not automatic legal claims.

External venue login/OAuth, physical device compatibility, owner-approved
pixel parity and production signing remain separate acceptance requirements.
No actual financial transaction was performed.
