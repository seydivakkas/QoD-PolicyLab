# QoD-PolicyLab — backend v0.1.0: implementation evidence and limitations

## Implemented on `feature/backend-v0.1`

- Strict `1.0` configuration/Observation schema and causal policy-only data view
- Seeded immutable external traffic/latency/jitter/provider trace with same time-indexed draws for all policies
- Best Effort, Static and heuristic Adaptive; target and approach eligibility gates
- Deterministic request, response, lease, failure, timeout and cooldown lifecycle
- Synthetic factor-model benefit applied *only* after a provider grant; no retroactive effect
- Fixed request fees, active-second charges and deadline miss penalties separated into service cost and utility loss
- Individual scenario runs and paired common-trace multi-seed comparisons (raw per-seed metrics retained)
- Offline generate/simulate/compare/report CLI with JSONL, CSV, JSON, checksums and static HTML
- `unittest` coverage and Windows/Linux Python 3.11/3.12 CI workflow definition

## Local reproduction

```powershell
py -m pip install -e .
py -m unittest discover -s tests -v
py -m qodpolicylab generate --config examples/demo_config.json --seed 42 --out runs/trace
py -m qodpolicylab simulate --config examples/demo_config.json --trace runs/trace/scenario.jsonl --policy adaptive --out runs/single
py -m qodpolicylab compare --config examples/demo_config.json --seeds 30 --out runs/paired
py -m qodpolicylab report --run runs/paired
```

## Limits / unfinished engineering work — no frontend approval

- Provider model has grant/reject/timeout branches, but not delayed callback idempotency, 503 fault-injection, external loss, duplicate response events or rescheduling.
- Adaptive policy is a transparent *heuristic*, not a held-out calibrated expected-utility estimator.
- No paired bootstrap confidence intervals, adverse-condition Pareto sweeps, locked stress benchmarks, external real network traces or backend acceptance thresholds.
- The `qod_latency_factor` is hypothetical; the system never invokes or promises a 5G provider SLA.
- CLI config schema is flat `1.0`, not the earlier nested `1.0-design` illustrative config.
- Windows CI execution is not verified until GitHub Actions run after push; distribution license not selected.

**Status:** executable backend foundation, module-level automated tests passed locally; full backend gate and independent real-data acceptance remain **HOLD**.