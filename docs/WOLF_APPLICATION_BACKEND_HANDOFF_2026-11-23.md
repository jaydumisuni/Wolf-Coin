# Wolf-Coin Application Backend — Versioned Integration Handoff

**Protocol:** `wolf.app.request.v1` / response `wolf.app.bridge.v1`. **Backend candidate:** `0.1.0a8`. This is an independent application backend, **not** a replacement for the nine-screen frontend, Wolf Browser, Chromium/CDP, D-XQT or the native application packaging.

## Transport and trust

The native Windows/Linux/Android host owns the bridge process and website credentials. The backend runs a **private child process using newline-delimited JSON on stdin/stdout**, never a network server or exposed HTTP port. First-time native host setup: `wolf-app-bridge --init-key APP_KEY`. This writes 32 random bytes at 0600 permissions on Unix, refuses overwrite and never prints the secret. For operation: `wolf-app-bridge --db PRIVATE_APP.sqlite3 --key-file APP_KEY`. Requests must have `auth_tag` equal to HMAC-SHA256 using the native key over the canonical JSON request excluding `auth_tag` (recursively sorted object keys, compact separators, UTF-8 without escaped non-ASCII). Do not expose that key to website JS. Unsigned or tampered messages fail. `--research-unkeyed` exists **only for local fixtures** and must never be configured by the installable native host.

On every native application launch, send a unique signed `host.startup` request with `{"host_instance_id":"unique_native_run_id"}`. Previously active sessions become PAUSED and in-flight observation jobs become UNKNOWN. Accounts and history are preserved. Wolf Browser then validates the restored authenticated session and sends `session.record ACTIVE` plus a **new** observation before financial data is current again. A persisted local label is not session validity.

All browser observations are classed UNVERIFIED until real provider acceptance. The backend never receives cookies, passwords, OTP, access/refresh tokens, DOM bodies, screenshots or raw network payloads. It receives normalized facts, a hostname-only origin and a SHA-256 evidence reference. Signed native IPC is not a guarantee of platform truth; only the native host can verify what an authenticated browser actually observed.

## Interface envelope

`{"schema":"wolf.app.request.v1","request_id":"unique_001","operation":"account.register","payload":{...},"auth_tag":"64_hex_hmac"}`

Every request returns one JSON object with the same request ID, `schema=wolf.app.bridge.v1`, `status=OK` or `REJECTED`, and `live_enabled=false` / `financial_execution_authorized=false`. Unknown or extra fields are denied. File `contracts/wolf-app-bridge-v1.schema.json` describes the envelope.

| Operation | Inputs / function | Intended existing screen |
|---|---|---|
| `bridge.capabilities` | Query protocol and restrictions | Settings, Security |
| `host.startup` | Native startup revalidation, ambiguous-work recovery | Sessions, Security |
| `account.register` | domain, account_id, platform_id, currency, display_name; permanent registration | Accounts, Platforms |
| `account.remove` | explicit account removal; local account/financial/session data deleted; native browser must delete matching cookies/profile | Accounts, Security |
| `accounts.list` / `account.read` | Registered accounts, status, source, device metadata, last-known balance and freshness | Overview, Accounts, Sessions |
| `session.record` | ACTIVE, LOGGED_OUT, EXPIRED, OFFLINE, PAUSED, observed_at, optional device_id and local session_ref | Sessions |
| `observation.ingest` | source DOM / ACCESSIBILITY / VISIBLE_NETWORK / SCREENSHOT; observed_at, hostname, evidence_sha256, bounded decimal fields and optional transaction list | Accounts, Financial Data |
| `financial.overview` | Currency-separated aggregates of *only* current unconflicted observations | Overview, Financial Data |
| `financial.history` | Bounded paginated OBSERVATIONS or TRANSACTIONS with optional timestamps | Financial Data, exports |
| `activity.list` | Bounded hash-chain-checked audit readback, not externally anchored | Activity |
| `sync.plan` | Read-only refresh recommendations, not clicks | Settings, Accounts |
| `sync.enqueue` / `sync.claim` / `sync.receipt` / `sync.reconcile` / `sync.cancel` / `sync.inbox` | Durable OBSERVE_ACCOUNT work; ambiguous effects never automatically retried | Browser, Activity |
| `decision.propose` / `decisions.list` / `decision.receipt` | RESEARCH_ONLY proposals and NOT_EXECUTED / CANCELLED / UNKNOWN receipts; no placement authority | Overview, Activity |

The backend will not add a tenth top-level UI screen. The KRATOS paper `/neural` and `/gates` pages are **development surfaces**, not approved product navigation.

## Evidence example

Native browser reports a successful account registration:

`{"domain":"sports","account_id":"account_001","platform_id":"example_platform","currency":"ZMW","display_name":"Example"}`

After `session.record ACTIVE` with the native host's nonsecret `session_ref` and UTC `observed_at`, ingest:

`{"domain":"sports","account_id":"account_001","observation_id":"obs_001","session_ref":"local_session_001","observed_at":"2026-11-23T14:00:00+00:00","source":"DOM","origin":"example.invalid","evidence_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","fields":{"cash_balance":"100.00","available_balance":"80.00","pending_bets":"12.00","realized_pnl":"-5.00","unrealized_pnl":"2.00"}}`

This is illustrative sample input, **not real account evidence**, and dates must be refreshed at integration. A native host computes the HMAC and supplies a request ID for each envelope.

## Financial invariants and recovery

Only bounded decimal strings are accepted: cash and available balances, pending bets/deposits/withdrawals, open exposure, realized/unrealized P/L, cumulative deposits/withdrawals and fees remain distinct. An observed transaction is keyed by domain/account/transaction identity and cannot silently change amount, type or timestamp; PENDING may advance once to SETTLED or CANCELLED. These are **source-reported statuses**, not externally confirmed settlements.

Snapshots retain timestamps and session lineage. Old observations cannot overwrite current ones. Cross-channel DOM and visible-network observations within 15 seconds are either CROSS_CHECKED_UNVERIFIED or CONFLICT; conflicted/stale snapshots are excluded from overview totals. Currency totals are separated; no USD/ZMW conversion is inferred. Logout, Offline, Expired and app restart preserve the last figures but mark them STALE_LAST_KNOWN. The current native host must explicitly revalidate session and capture new evidence.

The sync queue permits **one pending/claimed/unknown task per account**. A claimed job can only be DONE after its session produced a *new observation after the claim*. App restarts mark CLAIMED work UNKNOWN; they never replay it. Research decisions require fresh same-session evidence; no program path submits real orders or bets. The existing Guard, paper ledger, model research and Formula/SUP advisory boundaries are preserved.

## Deployment boundary and final acceptance

The backend itself requires Python 3.11+, standard-library SQLite and a private OS filesystem. It can be bundled natively on Windows/Linux without KRATOS, API keys or Docker. Android requires the frontend/native owner to embed compatible Python or port this protocol to the Android host—**a wheel is not an APK**. The browser/native host owns Chromium profiles, credentials, site authorization, app lock/biometric policies, packaging and pixel fidelity. Deleting an account from backend returns an explicit browser-credential-cleanup obligation.

Offline acceptance requires the exact wheel and signed native IPC to pass: account persistence, session expiration/revalidation, two-domain currency isolation, transaction settlement/idempotency, conflicting evidence, history pagination, work-queue crash safety, proposal/receipt safeguards, hash-chain audit and cross-process recovery. Actual live platform login, visual DOM verification and permitted website automation remain **joint integration acceptance** after both sides are complete.

No production permissions are implied: SUP typed method admission and market profitability remain unproven. Real-money use needs separate explicit venue permission, model/risk qualification, authoritative readback, owner authorization and Tenfold review.


## Native backup and restore

`wolf-app-backup --backup APP_STATE.sqlite3 --output NEW_PRIVATE_BACKUP.sqlite3` creates a consistent, **create-only** SQLite backup through the SQLite backup API and validates the hash-chain audit. `wolf-app-backup --restore PRIVATE_BACKUP.sqlite3 --output NEW_APP_STATE.sqlite3` refuses overwriting existing files, checks the original schema and integrity, then atomically copies into a new DB and changes restored ACTIVE sessions to PAUSED/UNKNOWN with a new audit event. Browser profile credentials are **never** included. The resulting backup includes sensitive account metadata, so the native app host must use its own private OS directory and provide encrypted-at-rest backup/key management. Raw backend SQLite copies are **not encrypted** by the standard-library module; do not export them to untrusted storage.

This backup CLI is for the trusted native host, not a browser page API. The backend's signed per-message IPC governs application state; host key rotation, OS keychain, app-lock and encrypted backup remain native host responsibilities.

## Local source acceptance

New isolated app-backend modules and native-host mock tests passed **49 application-facing tests**, with the entire Wolf-Coin regression suite at **378/378**. The pending native offline wheel and installed-host tests are recorded separately before source acceptance is advanced. The existing a6 PAPER service remains installed and unchanged during development. The historical model and SUP/Formula acceptance remain separate and are not reclassified as complete by these account tests.
