# QoD async mock provider and paired decision audit v0.1.2 — 2026-10-11

## Code boundary
- Opt-in `simulate --callback-delay-s 1.0 --request-timeout-s 0.6` activates deterministic `ProviderEventQueue` with explicit delivery time and correlation to request ID.
- The legacy `run(trace,cfg,policy)` synchronous path is unchanged by default.
- Provider callback outcomes still derive only from the current observation's pre-generated exogenous random draw, not future traces or policy-specific RNG consumption.
- Deadline timeouts are applied at their *scheduled time*, so a late GRANT cannot resurrect a resolved/expired session or backdate QoD benefit.
- `callback_audit.json` and SHA-256 manifest are written in async CLI mode.
- Policy compare now adds strict two-objective Pareto/non-dominated set (mean miss rate vs service cost) and seed with worst miss rate per policy.
- Full operator-like concurrency, variable callback latency distribution, retries and cancellations remain **unimplemented**.

## Open before backend v1
1. Random but precomputed non-leaking delay distributions; retries/cancellations across arbitrary event order, renewal and expiry.
2. Pre-registered development-vs-held-out experiments, calibrated expected utility, Pareto statistical uncertainty and independent worst-seed bounds.
3. Safety failure cases: provider 503/zero grant/no effect/timeout and resource-bounded memory for large scenarios.
4. Stable offline localhost API, packaging/licensing and comprehensive synthetic E2E.
5. **Frontend after backend, independent telecom traces LAST**.

Status: **DRAFT / HOLD**. No claim of real 5G latency improvement or commercial operator QoD.