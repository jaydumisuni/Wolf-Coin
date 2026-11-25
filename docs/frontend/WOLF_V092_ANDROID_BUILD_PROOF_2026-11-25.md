# Wolf-Coin Android 0.9.2 native qualification — November 25, 2026

Source: work/wolf-public-market-v092-20261125
Application com.thetechguy.wolfcoin, versionCode13, versionName0.9.2-dev.
Android 15 x86_64 emulator with independent WebView named account profiles,
embedded private D-XQT WebAssembly, and owner-controlled a10 Python3.11/SQLite
application backend through signed wolf.app.bridge.v2.

## Exact package proof

- Gradle8.7, Android SDK35 and Chaquopy17.2 built offline on KRATOS:
  BUILD SUCCESSFUL, 47 tasks, 14 seconds.
- Source APK SHA256:
  aa241285ce12052be4170385ad28be7fd20c8bc7aa74b2c2be9ad79271ef66c7
- Real ADB install and installed base.apk SHA256 readback matched source.
- Resumed native Activity, nine WebView tabs, D-XQT ready, independent
  account profiles and portfolio module passed:
  WOLF_APK_C10_STYLE_PROOF_PASS.
- Existing emulator data (13,258,240 bytes) was backed up and verified
  before package replacement. Previous lab accounts remained present.

## Native backend, session and portfolio

- A fixture-authenticated account produced K750 cash. The signed Python
  backend stored the financial observation and returned
  BROWSER_HANDOFF_READY for a synthetic contextual decision and recorded
  a NOT_EXECUTED receipt. No real-money action:
  WOLF_ANDROID_EMBEDDED_A10_E2E_PASS.
- After Android process restart, account persisted as PAUSED and
  STALE_LAST_KNOWN with K750 last-known data; website cookies restored,
  fresh observation revalidated ACTIVE and history increased:
  WOLF_ANDROID_EMBEDDED_BACKEND_RESTART_PASS.
- Two independently authenticated fixture site origins and named profiles
  synchronized through Android Sync All. Both reported OBSERVED with two
  separately recorded financial observations each; the frontend also
  returned suggested owner-match evidence, not verified legal ownership:
  WOLF_ANDROID_NATIVE_CROSS_PLATFORM_PAIR_SYNC_PASS.
- Backend Overview, Finance, balance history and Activity records rendered:
  WOLF_ANDROID_BACKEND_NINE_SCREEN_BINDING_PASS.
- Fixed a test expectation that wrongly treated one account's K750 as
  the total ZMW portfolio amount when previous accounts also existed.
  Multi-account test now scopes precisely to its own two account IDs.

## Not yet qualified

Production APK signing, a physical Android device, owner-approved pixel
parity, authenticated third-party broker/sportsbook login and real provider
result reconciliation. No new product restrictions were introduced.
The same corrected public quote extractor was tested on actual Windows
Chromium, not asserted as a new Android live-provider test.
