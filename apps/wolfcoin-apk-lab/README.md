# Wolf-Coin cross-host APK lab (Prime/Ptah borrowing)

Execution: Real Android SDK emulator x86_64 / API 35, on native Linux (KVM) or Windows (WHPX where enabled). An APK requires an Android runtime; Prime OS's current Linux desktop components and Ptah's Rust C10 contracts are not themselves Android kernels or emulator binaries. This lab does not pretend otherwise.

Evidence: The platform-neutral Node 22+ runner verify-apk.mjs uses actual ADB installation, installed base.apk SHA-256 readback, Android resumed activity proof, real WebView CDP, embedded D-XQT runtime, nine-tab/frontend bridge, multi-profile support, and ADB screen capture. It writes wolf-apk-proof.json and wolfcoin-android.png. These are Ptah C10-style package, application and screen readbacks; no direct call into Ptah's ptah-android-runtime Rust API or formal independent signer admission is claimed. The report does not include account secrets.

KRATOS usage:
  ANDROID_SDK_ROOT=/home/kratos/.cache/wolfcoin-android-sdk node verify-apk.mjs --apk /path/app-debug.apk --serial emulator-5580 --port 9224 --evidence /tmp/wolf-apk-proof
The emulator may already be started; setup-linux.sh prepares a new AVD when needed.

ATHENA/Windows usage: Install Android SDK command line tools and Node.js 22+ once, enable Windows Hypervisor Platform (WHPX) outside the script if required, then execute in PowerShell:
  .\setup-windows.ps1 -Apk "C:\path\app-debug.apk"
The runner checks real runtime evidence on Windows exactly as on KRATOS. Windows execution itself is not yet verified because ATHENA was not connected. This script never changes Windows hypervisor settings or reboots.

Android debug fixture: The debug build alone allows Android emulator host loopback http://10.0.2.2, and only debug builds enable WebView DevTools. Production HTTPS and package trust checks remain separate.

Additional proof: android-portfolio-e2e.mjs covers two separately authenticated emulator WebView sessions, owner-match suggestion, owner-confirmed grouping, quote comparison and backend candidate; android-restart-proof.mjs checks restart persistence and isolation from a new unregistered account profile. These are controlled local websites and not real betting/broker platform acceptance.

Do not replace or overwrite the owner's Prime OS or Ptah repositories. Portability is through Android SDK/ADB runtime; Ptah supplies an evidence design to adopt later when device controller integration is ready.

## v0.9 embedded Python backend tests

The Android APK now contains the frozen owner-controlled a10 Python backend
inside Chaquopy. The signed app backend is used by the trusted Android host.
Reproducible test files in this directory:
- android-native-backend-e2e.mjs: browser account registration, financial
  observation, signed backend history and synthetic decision/receipt
- android-native-backend-restart.mjs: persisted SQLite and cookie state after
  force-stop/restart and native session revalidation
- android-native-ui-data.mjs: actual backend Overview/Finance/Activity data
- android-native-multi-account.e2e.mjs: two distinct authenticated websites,
  independent backend histories and cross-platform Sync All

Windows APK lab has a setup script but Windows execution remains unverified.
