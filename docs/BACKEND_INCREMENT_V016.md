# Backend v0.1.6 — optional retry/backoff
Status DRAFT/HOLD. No network/provider integration, real 5G SLA or frontend.
RetryConfig and RetryGuard consume only causal session events and apply a
global request cap, transient failure budget, exponential capped delay.
A denial or explicit cancellation is not retryable. No provider RNG leaks.
The previous simulation default is unchanged; opt-in by passing
retry_config=RetryConfig(...) to simulation.run. The time-indexed provider_u
from the current tick remains the only exogenous provider draw.
This is synthetic model behavior, not an operator-approved renewal.
Held-out scientific policy acceptance, stress/resource limits and licensing
remain open. Independent real trace assessment is the FINAL phase.
