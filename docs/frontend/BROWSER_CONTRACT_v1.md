# Wolf Browser / Backend Integration Contract v1 (development)

The browser host reports schema wolf.browser.v1. This is a proposed observation boundary, not a broker or sportsbook API. Backend risk policy, account authority, identity, financial truth and execution rights remain with Wolf-Coin's independent backend.

Methods: status, showBrowser, hideBrowser, browserBounds, back, forward, reload, snapshot, inspectDOM, inspectNetwork, screenshot, action, clearSession, openExternal, onPageState.

showBrowser takes url and accountId; creates a real Chromium or WebView session isolated by account ID. Actual session validity/lifetime remains website controlled.

snapshot returns accountId, url, title, auth, authEvidence, observedAt, candidates, source and contract. Source carries accountId, url, observedAt, verification candidate_only, evidenceOrigin visible_dom.

Candidates balance, pending and pnl are nullable with currency, source label, confidence heuristic, verification candidate_only. They are NOT verified financial statements. Backend must reconcile them before treating them as authoritative.

inspectDOM supplies bounded visible-control descriptors, omits secret input types/field values. inspectNetwork supplies bounded request metadata with paths without query; no cookies, headers, secrets or response bodies. screenshot returns bounded, local-only PNG evidence. action supports account-scoped navigation, scrolling, clicks (including normal form submissions) and field entry. Website effects depend on the currently authenticated website session; this generic browser bridge does not select strategies or initiate actions independently.

clearSession clears local auth/storage, but cannot guarantee server-side revocation and MUST NOT delete the account registry record. Account records currently use UI local state; the backend will become authoritative upon integration.

Windows/Linux: Electron 37.2.6 WebContentsView with persisted account partitions. Android: AndroidX WebKit 1.13.0 profiles when supported; same-origin appassets message bridge. Android physical support is unproven.

Expected correlation fields: account identity, capture timestamp, source URL, currency, freshness, verification, evidence ID, action ID and status. The browser must never expose raw passwords or session cookies to the model/backend.


## v1 extension: portfolio and owner evidence

Browser snapshots may now include bounded identity observations (a labeled account holder display string from a currently authenticated website DOM) and normalized opportunity candidates (market, selection, kind, side, quote and currency). Both are explicitly candidate-only browser evidence and are never proof of beneficial ownership or profitability. Linking is owner-confirmed; independent authenticated session partitions remain unchanged. See PORTFOLIO_CONTRACT_v1.md for owner matching, currency-safe portfolio aggregation and wolf.action.request.v1. The backend remains the authoritative execution/reconciliation boundary.
