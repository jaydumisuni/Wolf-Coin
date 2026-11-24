# Wolf-Coin Portfolio & Owner Recognition v1 — offline integration boundary

Authority: This is a **frontend observation / portfolio interaction contract**, not a backend trading engine. The backend owns authoritative account registries, reconciled financial balances, risk, execution, durable decision receipts and cross-platform learning. No real-money activation occurred.

## 1. Account identity observations

Each Wolf Browser snapshot may include identity: {displayName, label, verification: browser_observation_only, confidence: heuristic}, derived ONLY from a labeled account-holder field in an authenticated website DOM. A login form alone, a matching nickname, a matching URL or a saved browser cookie is not proof of common legal ownership.

Frontend account fields: accountId, platformName, websiteUrl, browserSessionId (host-local), ownerEvidence {displayName,label,observedAt,url,auth,verification}, ownerGroupId (nullable), financialCurrency, source/capture time and last-known financial candidate fields. No passwords, raw session cookies, security questions, recovery codes or provider access tokens flow to the intelligence engine.

## 2. Matching and linking lifecycle

- Automatically propose wolf.owner.match.v1 when two separately observed authenticated owner-display labels normalize to the same canonical value. No auto-merge on weak or ambiguous evidence.
- A person approves the "Confirm Pair" action before ownerGroupId is assigned.
- A confirmed owner group contains stable member account IDs and retains each independent browser partition. Unlinking one account does not log out, delete or share its credentials. Removing an account causes the group to drop that member.
- A user logout or expired session keeps the registered account in its owner group. Financial values become last-known/stale. On application restart, formerly connected accounts begin Unverified until a browser observation revalidates them.

## 3. Portfolio view and currencies

The local candidate portfolio groups each ownerGroupId's accounts, then totals balances, pending exposure and net P/L **only within the same ISO currency**. Never add K and USD without a provider/backend exchange-rate contract. A mixed-currency top-level summary is marked non-additive rather than silently combined. Each group shows how many account figures are stale. These are browsing candidates, not audited portfolio statements.

## 4. Opportunity comparison

Normalised opportunity candidate fields:
  market, selection, kind (bet|trade), side (back|buy|sell),
  quote, currency, accountId, sourceUrl, capturedAt, sourceEvidenceId,
  verification=candidate_only, confidence=website_dom_observation.

The browser's generic extractor currently admits explicit safe DOM fields, demonstrated by controlled local fixtures. Real platform DOM adapter evidence remains per-site acceptance. The comparison layer matches owner group + market + selection + kind + side + currency, only while both source accounts are connected and the observations are newer than 24h. Betting/back compares higher decimal odds; trading/buy compares lower quoted price; trading/sell compares higher quoted price. This is quote comparison only, not probability calibration or proof of profitability.

## 5. Action request, never silent effects

Frontend queues wolf.action.request.v1:
  id, idempotencyKey, ownerGroupId, accountId, platform,
  candidate {market,selection,kind,side,quote,currency},
  source {evidenceId,capturedAt,url,verification:candidate_only},
  status, createdAt.

A repeated candidate request returns the original request ID. The frontend can send it to an injected backend adapter's proposeAction(request); otherwise it retains it locally with status pending_backend. An event wolf:action-request may notify an integration adapter. The backend adapter determines how requests are handled, including any website interactions, verification, results, and receipts, according to the owner’s backend implementation. This contract is intentionally compatible with the user's separately developed Wolf-Coin backend.

## 6. Verified acceptance and boundaries

- Native Electron/Chromium two-fixture test: two account registrations, separate website logins, automatic owner-match suggestion, owner-confirmed group, odds 2.1 vs 2.3, one queued candidate, persistence after application UI reload — PASS.
- Android API35 x86_64 emulator with WebView124: same two-fixture flow PASS; restart retained two accounts/group/request; authentication restored in its original WebView profile; a freshly created third profile could not reuse the login cookie — PASS.
- Ptah device C10-style APK evidence: installation SHA256 readback from on-device base.apk, resumed activity, real WebView, D-XQT, nine screens and screenshot capture — PASS on KRATOS emulator.
- Windows portable Android emulator harness is provided, but not executed under Windows: ATHENA was offline.
- Real legal ownership recognition, live quote coverage, provider terms/permissions, backend reconciliation, strategy learning, live action and independent financial execution acceptance are **not** proven by fixtures.

## v0.8 signed native account coordination

Desktop Sync All invokes the current browser partition for each registered
account, collects page evidence and sends signed session/observation records
to the backend. Two-account integration passed on KRATOS.
The frontend sends normalized comparison candidates to the signed backend
through a user-editable amount and optional budget entry when no amount is
provided. The backend returns the context-driven next step and receipt state.
Merely creating a proposal does not establish a website transaction result.
