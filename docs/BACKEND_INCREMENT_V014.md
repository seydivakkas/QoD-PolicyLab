# QoD-PolicyLab — Backend increment v0.1.4: exact synthetic timer boundaries

**Status:** Offline mock QoD only; backend acceptance **HOLD**.

## Engineering changes

- `Session.advance(t)` validates monotonic finite local time, processes zero or more expired events in order, and records provider setup completion, lease expiry, cooldown completion, and request timeout at their **scheduled timestamp** instead of the next coarse observation tick.
- Asynchronous callback queue continues correlating with request IDs; timeout resolution is irreversible, and duplicate/late callback cannot create active service.
- `simulation.run(..., max_requests=N)` optionally caps requests (a **retry budget**, not a new renewal implementation). Default is unbounded and compatible with previous callers. The optional result records exhaustion.
- Active service accounting caps a sample interval at known lease expiration. This avoids counting beyond lease, but is still a discrete sampled approximation; no externally calibrated billing claim.
- Added synthetic tests for coarse timestamp progression, timeout vs late grant, non-monotonic time, request cap, and lease-bound cost.

## Still open

- Explicit in-session lease renewal and cancellation, randomized-but-paired provider delays, exact continuous-time event integral, full event-order fuzzing and robust operator-like retries/backoff are **not completed**.
- Calibrated policy weights and independent frozen synthetic holdout, p99 guardrails, formal fairness and risk checks are open.
- No telecom integration, SLA, QoD entitlement, or real traffic data. **Frontend only after backend acceptance; real-data analysis last.**
