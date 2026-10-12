# QoD-PolicyLab — backend v0.1.7 frozen synthetic holdout

## Implemented

- `python -m qodpolicylab.heldout_acceptance --out DIRECTORY`: **read-only** synthetic policy comparison across a predeclared, non-tunable eight-seed set (14200–14207), five profiles (reference, no QoD effect, zero grants, provider 503, slow setup), all three policies and three variants (legacy, capped retry, async with cancel+renew).
- The exact same synthetic exogenous trace is reused for all policies/variants *within each seed/profile*. The model never calls an actual mobile network provider.
- Negative controls assert no fictitious latency improvement or active QoD on zero-grant/unavailable cases; bounded variants enforce request budgets and prohibit legacy/ordinary retry from renewing lease.
- Preserve **all rows**, seed-wise worst misses/cost, mean misses/cost/utility and all violations. A SHA-256 manifest is generated, with overwrite refusal. Tests ensure every predeclared pair is included.

## Limits / HOLD

This is a synthetic consistency and counterfactual **report**, not policy superiority. `performance_acceptance` is **NOT_ESTABLISHED** by design; no thresholds are tuned on the holdout. It cannot validate operator ACKs, cancellation SLAs, real QoD or actual radio-network benefits. Final independent synthetic policy criteria, memory/latency stress, licensing and end-to-end installation still need separate acceptance. Real telecom traces strictly LAST.