# Wolf-Coin 0.9.6 — user-selectable web search

Date: 2026-11-26. Branch: work/wolf-order-entry-session-20261125.

## Owner decision

Google account login is not a prerequisite for the Wolf browser. Public web
search works without a Google session. The owner selected **Google as the
default** search provider and requested the ability to select another provider
(Bing). No Google OAuth or account-linking integration is introduced.

## Implementation

- First-run/default setting: `searchEngine: google`.
- Settings > Browser > Default search engine: **Google** or **Bing**.
- Search words in the header address bar or Browser omnibox become the
  chosen provider's encoded query URL. URLs/domains navigate directly.
- Existing saved setting survives renderer reload and application restart,
  including pre-0.9.6 profiles whose state lacks the new key (merged with
  the new default). Unrecognized settings fall back to Google.
- No additional visible browser toolbar (preserves approved compact layout).
- Search does not require credentials, and the provider selection does not
  access or change per-site browser cookies or password vault.

## Controlled native browser acceptance

- WOLF_SEARCH_ENGINE_PREFERENCES_PASS: Google first-run, selected Bing,
  reload persistence, return to Google, both address bars, direct URL,
  invalid-value fallback.
- WOLF_SEARCH_AND_DIRECT_NAVIGATION_PASS: Chromium reached Google's search
  URL, Bing returned visible public results, and direct local fixture URL
  navigated without being converted to a search.
- WOLF_COMPACT_BROWSER_UI_E2E_PASS: browser viewport/layout, responsive
  sidebar, 47 currencies, manual user preference; no duplicated header.

Provider-side traffic verification may block Google results in some sessions;
the application must display those pages faithfully and cannot promise
provider access or circumvent Google verification. Bing offers an optional
alternative. No real-money site or Google account was used.

## Remaining release gates (separate from this change)

Graphical installer wrapper requires C: and Builder-drive disk preflight;
original Android production signing-key continuity and physical hardware
qualification require real device/key evidence. Provider-specific live
bet/trade acceptance requires authorized accounts, real platform observation
and signed execution receipts. The 0.9.5 title bar and prior native
application functionality remain unchanged by this search preference update.
