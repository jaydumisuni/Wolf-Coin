# Wolf-Coin v0.9.2 public market recognition — evidence and boundaries

Date: 2026-11-25
Source branch: work/wolf-public-market-v092-20261125
Previous baseline: v0.9.1, commit 4b4cd0210caa608ac064b4f7fc578acb1699ffef

## Recovered issue

The real v0.9.1 ATHENA Windows build loaded Google Finance's public
https://www.google.com/finance/quote/GOOGL:NASDAQ page, but Wolf Browser
reported probable_authenticated and unclassified. Its old accountHeader
regexp treated a public "Create a portfolio" link as logged-in evidence.
The public instrument price was not represented as a structured quote.
The public https://www.betpawa.co.zm/ sportsbook landing page initially
had no DOM while loading but later completed, showing a visible sign-in
control and sports-betting title without exposed market odds.

## Correction

- Explicit visible sign-in controls have priority over generic account-like
  headings unless a genuine sign-out control is observed.
- A public "Create a portfolio" promotion is not logged-in evidence.
- Public quote extraction cross-correlates symbol/instrument in visible
  document title and URL, observed numerical quote and currency in nearby
  visible DOM text. Result is marketQuotes[], verification candidate_only,
  source visible_title_url_and_currency.
- Public stock prices are not actionable broker buy/sell controls.
  They do not produce opportunities[] without separate actionable evidence.
  Classification is market_data, not trading.
- Source is identical for desktop Chromium and Android WebView.
  No product-category execution restriction or security policy was added.

## Proved on genuine ATHENA Windows Chromium targets

Executing the patched extractor against real loaded website DOM in an
isolated v0.9.1 Wolf-Coin Chromium process (not editing the installed app):
- Google Finance: auth=unverified, signInControlVisible=true,
  category=market_data, basis=public_price_evidence,
  marketQuotes GOOGL:NASDAQ USD 264.91 at capture time,
  opportunities.length=0. Historical test sample, not current price.
- betPawa Zambia: auth=unverified, category=betting,
  basis=visible_site_heading, marketQuotes=[], opportunities=[];
  no invented odds.
- Local authenticated fixture: auth=probable_authenticated,
  genuine Log Out control, K750 cash, K100 pending, K60 P/L.
  WOLF_PATCHED_LIVE_PUBLIC_AND_AUTH_FIXTURE_PASS

## Source and integrated regressions

node apps/wolfcoin-desktop/tests/public-market-extractor.test.cjs
passed: WOLF_PUBLIC_MARKET_DOM_EVIDENCE_REGRESSION_PASS

Real Linux Chromium/Electron using the new source and frozen private
D-XQT/native backend passed:
- WOLF_NATIVE_UI_E2E_PASS (nine screens, browser tools, login/logout)
- WOLF_NATIVE_FINANCIAL_ACTIVITY_UI_PASS (one account, five observations,
  thirteen audit events, native finance/history)

The installed v0.9.1 release does not include the patched extractor.
Windows/Android v0.9.2 binary qualification is a separate packaging gate.
