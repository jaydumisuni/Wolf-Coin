# Wolf-Coin v0.9.6 — selectable search engine

Owner request: remove forced Bing for searches and make Google default,
with Bing remaining available as the user-selectable alternative.

## Implementation

- The only authoritative UI source is apps/wolfcoin-ui/ui-template.html.
- DEFAULT_SETTINGS.searchEngine = "google", merged into existing saved UI
  preferences. Existing registered accounts, cookies, per-account browser
  profiles and native backend data are not modified by this upgrade.
- Settings > Browser now contains a Default search engine selector
  (Google / Bing). Selection persists using Wolf's existing local settings
  and carries through the standard UI preferences backup.
- Both the top address bar and the Browser-specific address bar route
  searches through the same searchQueryUrl() provider mapper.
- Provider URL maps are explicitly enumerated, percent-encode query text,
  and fall back to Google if an unsupported provider ID is encountered.
- Explicit HTTP(S) web addresses and hostname-like inputs continue to
  use direct navigation, independent of search engine preference.
- Android and desktop assembled HTML share the same source template.
- Private D-XQT runtime remains local and is never committed to GitHub.

## Controlled evidence

- WOLF_SEARCH_ENGINE_PREFERENCES_PASS on isolated native Linux Electron
  profile: initial Google default; top-bar Google query URL; Settings >
  Browser select renders two providers; switch to Bing; Browser query
  uses Bing; saved preference survives renderer reload; switch back to
  Google; Browser query uses Google; explicit HTTPS URL unchanged; invalid
  provider ID falls back to Google. No change to account/credential state.
- v0.9.6 source passes Node static JS checks and Git diff whitespace checks.
- Android QA package v0.9.6-dev/versionCode 18 builds successfully with
  an exact bundled-HTML vs assembled-source SHA256 match.
- Linux rootless Debian install/launch/remove passes nine-view app
  registration, native login, backend finance and Activity regression.
  wolf-coin 0.9.6~dev1 then installed on KRATOS with HTML source parity.
- Search-provider test verifies application navigation semantics, not
  Google's or Bing's external availability, rankings, or CAPTCHA response.


## Additional native browser acceptance

- WOLF_SEARCH_AND_DIRECT_NAVIGATION_PASS in isolated Chromium: Google
  search destination reached successfully; switching to Bing returned
  accessible public results, and the local fixture opened as a direct
  URL. Provider-side Google traffic-verification challenges remain
  outside Wolf's control and are not bypassed.
- WOLF_COMPACT_BROWSER_UI_E2E_PASS: browser viewport and utility sidebar
  geometry unchanged; 47 currencies and manual selection remain intact.
- Google account login is not required, and switching search provider
  neither alters saved credentials nor signs in to third-party websites.

## Installed package and Builder readback

- ATHENA installed Wolf-Coin v0.9.6-dev was updated from the separately
  tested Windows QA application, preserving the existing browser/profile
  directory. Old v0.9.5 resource files are retained with SHA256 manifest
  under `resources/app-backup-v095-before-v096-20261126`. The installed
  GUI was reopened successfully.
- WOLF_SEARCH_ENGINE_PREFERENCES_PASS on ATHENA Windows controlled
  Chromium with the v0.9.6 desktop HTML and owner-held D-XQT.
  Compiled app HTML SHA256:
  `e2a4f82179a18774a2e0e79620204dccfa301f6eac84ce5706ec62c452443d5e`.
- THETECHGUY Software Builder, existing `windows-exe` target, completed
  successfully on ATHENA. Electron NSIS setup and unpacked app built,
  actual program launched in Builder runtime smoke test, and ASAR HTML
  was SHA256-equivalent to the tested v0.9.6 source.
  Private NSIS archived at:
  `D:\projects\THETECHGUY Software Builder\builder_artifacts\Wolf-Coin\v0.9.6-dev\Wolf-Coin Setup 0.9.6-dev.exe`
  SHA256 `61ff6b8c2c175f3171f3a96bb7f43c07a5efad9718362ae59f30c0d3fbdb7561`.
  It is unsigned; this does not claim a release-signing certificate.
- Android v0.9.6-dev QA/versionCode 18 installed and package hash read
  back exactly on an Android 15 API35 emulator. The same
  `WOLF_SEARCH_ENGINE_PREFERENCES_PASS` verified Google, Bing,
  persistence, both address bars and direct URLs in its live WebView.
  APK SHA256:
  `3c85b7a0866e8434f003df8526ec386e42e162332a0561cb11a9fa3d245692f0`.
  The original Android production package and signing identity remain
  unchanged and need separate qualification for production rollout.
- Linux `wolf-coin 0.9.6~dev1` installed on KRATOS; installed app HTML
  matches its native Debian package by content hash.
- Private Debian and Android QA artifacts are frozen under
  `/home/kratos/projects/Wolf-Coin/.workspace/releases/wolf-v0.9.6-dev1`
  with SHA256SUMS. Temporary QA profiles, local extracted private
  runtime and duplicated packaging output were cleaned without touching
  installed profiles or the Builder executable.

## Contribution classification

Update existing documentation. This extends the browser search provider
selection without changing the backend decision system, user profiles or
the previously proven native window controls.

## Native process restart and cross-platform search acceptance

- Installed Linux wolf-coin 0.9.6~dev1, isolated user-data: Google default
  observed, Bing manually selected, localStorage record verified as Bing,
  normal Wolf window Close completed, then a fresh native process using
  that same isolated profile reopened with Bing selected. The test restored
  Google afterward. An abrupt SIGTERM immediately after saving had not
  preserved the last update; that is not a qualified power-loss durability
  path and is separate from normal shutdown persistence.
- Android emulator com.thetechguy.wolfcoin.qa v0.9.6-dev, versionCode 18:
  WOLF_SEARCH_ENGINE_PREFERENCES_PASS against the real appassets WebView;
  Google default, Bing selection, reload persistence, direct URL.
- Windows Builder-generated isolated v0.9.6-dev application on ATHENA:
  WOLF_SEARCH_ENGINE_PREFERENCES_PASS; no user account profile changed.

## Completed ATHENA graphical-installer acceptance

2026-11-26: the installed THETECHGUY Software Builder's full
windows-installer target was rerun against v0.9.6-dev staged source and
owner-held D-XQT assets. Its native Electron/NSIS packaging, runtime launch
test, custom graphical shell, installer package validation and graphical
dry-run completed. Builder recorded 12/12 stages complete, ok: true,
dry_run_passed: true, validation_exit_code: 0.

Private owner-only Windows release artifacts are archived on ATHENA in:

%LOCALAPPDATA%\THETECHGUY\Wolf-Coin\releases\v0.9.6-dev\

- Wolf-Coin Setup 0.9.6-dev.exe — THETECHGUY custom graphical installer,
  208,044,704 bytes,
  SHA256 37bede84b5fa3c098b82647c52088697cd9f4d3cb4730e65e822f84e06dbf312.
- Wolf-Coin NSIS Setup 0.9.6-dev.exe — standard NSIS installer,
  105,462,287 bytes,
  SHA256 61ff6b8c2c175f3171f3a96bb7f43c07a5efad9718362ae59f30c0d3fbdb7561.
- Also present: SHA256SUMS.txt, windows-gui-installer-dryrun.json,
  and target-execution.json.

Builder's previous D: space preflight was resolved through a reversible
maintenance operation. D: uses exFAT (not NTFS), so no filesystem junctions
were used. Nine old Builder installer-shell cache snapshots were temporarily
copied to C: with SHA256 verification and then restored to their original
D: paths with every file hash rechecked after build completion. The new
rebuildable v0.9.6 Windows single-file work cache and generated lean shell
cache were themselves preserved under
%LOCALAPPDATA%\TTG-Builder-Spill\ with recovery records, allowing D:
space to be restored near its original level (~328 MB free). The v0.9.6
standard installer was relocated from Builder's D: artifact folder into
the private C: release folder with checksum verification; the Builder
folder retains its proof reports and STANDARD_NSIS_LOCATION.txt pointer.
The older v0.9.5 installer and prior project artifacts remain untouched.

The graphical installer build and dry-run are now qualified; no production
code-signing certificate was configured. Its real end-user installation
and rollback on an independent external PC, original Android signing-key
continuity, physical Android qualification and third-party provider
financial execution/readback remain separate evidence gates. They are not
misrepresented as completed by controlled lab testing.
