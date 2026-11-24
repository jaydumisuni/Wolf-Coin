# Wolf-Coin native Android browser v0.6 — development

One APK project with nine-screen bundled UI and same-origin WebMessage bridge. Each website account uses a separate AndroidX WebKit named profile when MULTI_PROFILE is supported. If unavailable, managed website login is refused rather than sharing account cookies. The UI has no browser cookies, and no website receives the privileged WolfHost JavaScript interface.

Native browser operations: show/hide/navigate, bounded DOM inspection, website screenshots, read-only network request metadata, bounded click/fill/scroll (financial/secret controls denied), snapshot candidates, account session wipe, and page-state callbacks. Cookies are retained by WebView profiles when the website permits persistence; logout wipes profile cookies and web storage. No third-party account is tested.

Build: JDK 17+, Android SDK platform 35, Gradle 8.11.1+ and Android Gradle Plugin 8.9.1, with AndroidX WebKit 1.13.0; `gradle :app:assembleDebug`. `wolfcoin.html` contains the real D-XQT v8 binary already embedded.

Not qualified: physical Android installation, JavaScript bridge and profile behavior on specific WebView versions, OAuth popup compatibility, platform financial data reconciliation, financial execution or background autonomy.
