# Wolf-Coin shared frontend — owner-held private D-XQT

The full Chromium and Android Wolf-Coin user interface is preserved in ui-template.html, including artwork and the nine interactive tabs. The single-file D-XQT runtime is an owner-held PRIVATE build ingredient; it must not be committed to the public Wolf-Coin repository or added to a public release artifact. The browser-host code remains public-safe and separate from native financial execution.

Build on the authorised development workstation with the actual private runtime:
  python3 apps/wolfcoin-ui/assemble.py --dxqt-js /private/owner/runtime.js --desktop apps/wolfcoin-desktop/app.html --android apps/wolfcoin-android/app/src/main/assets/wolfcoin.html

A non-authoritative design-only preview can be built with --preview, but **must not be shipped or passed off as a working D-XQT runtime**.

Desktop and Android app.html/wolfcoin.html are generated/private delivery files and are ignored by Git. Do not overwrite the training/backend branches.

Portfolio owner grouping and cross-platform comparisons are supplied by apps/wolfcoin-portfolio and bundled at assembly; backing authoritativeness remains the independent backend.

v0.8 desktop assembly now includes backend_ui.js, binding Overview, Finance,
Activity, audit history and report/export functions to the signed native
application backend. Android compilation remains WebView-based while the
native backend host is developed independently.
