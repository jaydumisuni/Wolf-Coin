# Wolf-Coin portfolio frontend adapter v1

This adapter operates on already authenticated Wolf Browser observations and UI state. It does not determine legal ownership from identical names alone: it automatically suggests same-owner matches when separately observed, authenticated account-holder labels match, then requires owner confirmation to link. Separate account credentials and browser partitions remain isolated.

Linked portfolios aggregate **per currency only**, retaining a stale count. Candidate observations remain candidate-only and are not authoritative financial statements.

Comparisons group current (<24h) normalized quotes for identical market, selection, side, currency and linked owner. These are observational comparisons, not model strategy signals, expected-profit calculations or purchase/sportsbook submissions. Action requests carry idempotency keys and source evidence to the independent backend authorization boundary.

See tests/portfolio-core.test.cjs for deterministic contract proof. Backend strategy, risk and execution remain owned separately.
