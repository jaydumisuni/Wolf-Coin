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

## Contribution classification

Update existing documentation. This extends the browser search provider
selection without changing the backend decision system, user profiles or
the previously proven native window controls.
