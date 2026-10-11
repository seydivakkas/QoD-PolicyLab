# Backend gate ledger — v0.1.1 (2026-10-11)

## Change set and evidence

- `Session.provider_callback(time, request_id, outcome)` strictly correlates responses to an existing request, rejects premature/future ID/invalid outcomes and ignores repeated or stale replies without double charging, duplicate grants or session resurrection.
- `provider_service_unavailable_probability` explicitly models a hypothetical provider `SERVICE_UNAVAILABLE` (503-like) outcome. Counters are separated from reject and timeout. Outcome probabilities cannot exceed one.
- The deterministic provider still auto-dispatches at its modeled setup time; callbacks are an *engine contract*, not a real network adapter. Arbitrary asynchronous delivery, retry scheduling and lease renewal remain outstanding.
- `all_service_unavailable` added to the predeclared synthetic negative-control sweep; false QoD benefit under 503 is a regression failure.
- Four additional automated tests cover early/unknown/duplicate/late responses, provider 503 fallback and fixed synthetic sweep.

## Reproduce

```powershell
py -m pip install -e .
py -m unittest discover -s tests -v
py -m qodpolicylab sweep --config examples/demo_config.json --seeds 30 --out out/qod-negative-controls
```

The provider is mocked. Latency and service cost are simulated assumptions; no telecom API, real network QoS improvement or SLA claim is made.

## Still BLOCKED before backend acceptance

1. Advance from synchronous mock to deterministic asynchronous delivery schedule with bounded retries and late-callback expiry, without future peeking.
2. Calibrate expected utility only using predeclared development traces; hold out final synthetic scenarios and retain a no-QoD negative control.
3. Build Pareto frontier, worst-seed guardrails, confidence intervals and complete resource-bound tests with locked hypotheses.
4. Define stable local backend API and package/license review; preserve seed/trace reproducibility and audit outputs.
5. External 5G/real trace evidence only in the final separate stage, after frontend.

**Gate:** backend-in-progress; frontend HOLD; real-data HOLD.