# QoD-PolicyLab

**A reproducible, offline-first decision-policy simulator for on-demand quality-of-service (QoD) activation under deadline, latency, reliability and cost constraints.**

> **Status (feature/backend-v0.1): runnable offline simulator backend, not a real 5G QoD service or validated provider integration.** Synthetic policy replay, tests and audit reports are implemented. Full backend acceptance and frontend remain **HOLD**. See [`docs/BACKEND_V010.md`](docs/BACKEND_V010.md).

## 1. Why QoD-PolicyLab?

A safety-relevant or time-critical application can experience bursts in network latency, jitter and packet loss. Requesting better Quality of Service for every frame or event is potentially expensive and often unnecessary; requesting it too late may miss the deadline. The research problem is to choose **when to request an optional temporary QoD session**, and when to remain on ordinary best-effort connectivity, under transparent simulated network assumptions.

QoD-PolicyLab evaluates the trade-off between:

- Deadline miss probability, end-to-end latency and jitter;
- Request/activation delay, rejection, timeout and lease expiry;
- Resource use and an explicit synthetic monetary/utility cost model;
- Decision uncertainty, false activation and missed opportunities;
- Baseline policy performance, worst-case runs and distribution shifts.

It compares three causal strategies on matched traces: **Best Effort**, **Static Threshold** and **Adaptive Cost/Deadline-Aware**. It does not assert that QoD creates a fixed real-world speed-up.

## 2. Scope, assumptions and non-goals

**In scope:** offline network-quality trace playback, deterministic event engine, finite-state QoD session model, mock provider outcomes, explicit QoD improvement models, cost accounting, causal policy selection, fair paired experiments, robustness sweeps, audit logs and a local report dashboard.

**Out of scope for the first release:** real 5G modem control, real network slicing, operator provisioning, carrier authentication, live CAMARA API calls, guaranteed URLLC delivery, medical/automotive safety certification, comparison using unconsented personal network traces or claims of measured operator SLA improvement.

The policy engine controls an **abstract simulated session**. `ACTIVE` means the simulator's mock provider reports availability after modeled setup delay. A provider rejection, unavailability or timeout must always fall back to best effort; no algorithm may assume immediate QoS after sending a request.

## 3. Simulation boundary and terminology

| Term | Meaning in this lab |
|---|---|
| Best Effort (BE) | Baseline trace with no optional QoD session |
| QoD request | Policy-initiated request to the mock provider |
| Setup delay | Modeled time before a request may become available |
| Lease | Maximum active time until expiry or release |
| Deadline miss | Completion latency exceeds the scenario's deadline |
| `AVAILABLE` | Mock provider says QoD is granted; no real-network guarantee |
| Synthetic gain | A configurable latency/jitter/availability transformation, **not a measured 5G improvement** |
| Cost | Researcher-defined synthetic request/active-time/penalty units; not a carrier invoice |

The CAMARA Quality on Demand API can expose session creation and status lifecycle; this lab models selected concepts for experimental use but is **not an official CAMARA client or standards-conformance implementation**. A future adapter would need separately versioned mapping, credentials, authorization and contractual approval.

## 4. Architecture and isolation

```text
Scenario manifest + immutable exogenous trace events
                        |
                        v
        schema checks, timestamp ordering
                        |
                        v
             observation generator
        (past/current conditions only)
                        |
           +------------+------------+
           |            |            |
           v            v            v
     Best Effort     Static         Adaptive
           |            |            |
           +------------+------------+
                        |
                        v
              deterministic FSM
        IDLE / OBSERVE / REQUESTING
        ACTIVE / COOLDOWN / FAILED
                        |
                        v
       seeded event-indexed mock provider
                        |
                        v
          time-aware network model
                        |
                        v
      deadlines, requests, cost, fallbacks
                        |
                        v
      paired comparison + Pareto + audit
```

**Independence:** network, provider, policy and metric modules communicate through typed interfaces. Different policies see the same **exogenous** scenario, but their actions may legitimately lead to different outcomes.

## 5. Proposed package / module contract

| Module | Responsibility | Key contract |
|---|---|---|
| `qodpolicylab/scenario/schema.py` | Validate scenario trace and dimensions | Typed observations and immutable exogenous events |
| `qodpolicylab/scenario/generator.py` | Create burst, congestion, target-presence patterns | Config + seed → replayable events |
| `qodpolicylab/policies/base.py` | `decide(obs, state)` abstract interface | Causal action; no future or truth labels |
| `qodpolicylab/policies/best_effort.py` | Never request QoD | Deterministic zero-request baseline |
| `qodpolicylab/policies/static.py` | Request when configured threshold is met | Explicit severity threshold and eligibility |
| `qodpolicylab/policies/adaptive.py` | Deadline-aware cost-benefit policy | Unit-normalized features and uncertainty penalty |
| `qodpolicylab/fsm/machine.py` | QoD lifecycle and invalid transitions | Single current state + event/expiry rules |
| `qodpolicylab/provider/mock.py` | Provider accept/reject/delay/failure behavior | Replayable outcome keyed to exogenous request opportunity |
| `qodpolicylab/network/model.py` | Baseline/QoD delivered latency/jitter | Versioned counterfactual transformation |
| `qodpolicylab/cost/model.py` | Request, activation, and penalty costs | Same tariff parameters for all policies |
| `qodpolicylab/metrics/compare.py` | Paired evaluation and guardrails | Per-seed outcomes, CI, effect sizes, cost/miss Pareto |
| `qodpolicylab/report/` | Local timeline, CSV/JSON, SVG/HTML report | Full traceability from result to scenario and decision |
| `qodpolicylab/cli.py` | Offline CLI | Config in, reproducible run directory out |

These paths are **proposed**; they are not currently implemented.

## 6. I/O schema and example scenario

One event/observation per simulation tick, with external environment variables fully recorded:

```json
{
  "schema_version": "1.0-design",
  "scenario_id": "burst_001",
  "timestamp_s": 12.5,
  "latency_ms": 85.0,
  "jitter_ms": 12.0,
  "packet_loss_rate": 0.02,
  "severity": 0.8,
  "uncertainty": 0.3,
  "target_present": true,
  "approaching": true,
  "deadline_ms": 110.0
}
```

**Schema rules:** `timestamp_s` finite and monotonic, `latency_ms/jitter_ms >= 0`, `packet_loss_rate`/`severity`/`uncertainty` within `[0,1]`, `deadline_ms > 0`, booleans explicit, and missing values never silently interpreted as zero. The schema must define whether latency is a measured historical observation or the present sample. Any policy feature can depend only on data observable at the policy decision timestamp. Do not expose future latency or a counterfactual QoD outcome to policies.

### Simulation configuration (illustrative values, not field evidence)

```json
{
  "schema_version": "1.0-design",
  "seed": 42,
  "duration_s": 120,
  "tick_s": 0.1,
  "policies": ["best_effort", "static", "adaptive"],
  "provider": {"accept_probability": 0.8, "setup_delay_s": 1.0, "lease_s": 10.0, "cooldown_s": 5.0},
  "network": {"qod_latency_factor": 0.67, "qod_jitter_factor": 0.8},
  "cost": {"request_fee_units": 1.0, "active_second_units": 0.2, "deadline_miss_penalty_units": 3.0}
}
```

**Crucial:** `qod_latency_factor = 0.67` is a controllable **hypothetical scenario** corresponding to a 33% modeled reduction, **not** evidence that 5G QoD reduces latency by 33%. Evaluate `factor = 1.0`, ineffective boost and adversarial conditions, too. Scenario costs use synthetic units, not prices.

## 7. Decision policies and causality

### Policy A — Best Effort

Always stay on the baseline network, `request=False`; it is the explicit no-fee reference for incremental value. If missed-deadline penalties are tracked, they may still make *total utility loss* nonzero, even though **QoD request/service cost = 0**.

### Policy B — Static Threshold

Request when all eligibility conditions are met and `severity >= threshold`. Use the same target-presence and approach gating rules as adaptive where required by the experimental question. Boundary cases `threshold ± epsilon` must be deterministic. Do not request while requesting, active or cooling down.

### Policy C — Adaptive Decision

Estimate *expected marginal* avoided deadline misses or utility improvement based on **observable** latency, jitter, severity, approach, deadline slack, prior failure statistics and uncertainty. Compare against marginal request cost, predicted setup delay and failure risk. Suggested decision form:

```text
eligible = target_present AND approaching AND state_allows_request
expected_net_benefit = E[loss_if_BE | history] - E[loss_if_QoD_request | history]
request = eligible AND expected_net_benefit > configured_gate
```

The estimator must be calibrated exclusively on development data; feature values with incompatible units must be normalized. `uncertainty` must reduce confidence or adjust risk as justified, **not automatically be rewarded by a positive arbitrary weight**. Unknown parameters should trigger a reproducible conservative fallback.

No policy can inspect later frames, future provider successes or simulator ground-truth labels. A benefit estimator trained/evaluated on the same final seeds is prohibited.

## 8. Session state machine (FSM)

```text
IDLE -> OBSERVE -> REQUESTING -> ACTIVE -> COOLDOWN -> IDLE
  ^       |             |          |           |
  |       |             +-> FAILED-+           |
  +-------+------------------------------------+
```

**States:** `IDLE`, `OBSERVE`, `REQUESTING`, `ACTIVE`, `FAILED`, `COOLDOWN`.

| Current state | Event | Next state | Required effect |
|---|---|---|---|
| IDLE | Start trace / observation | OBSERVE | No provider session exists |
| OBSERVE | Policy eligible & requests | REQUESTING | Allocate unique request ID; account fee |
| REQUESTING | Provider grants after setup | ACTIVE | Mark grant time; start lease |
| REQUESTING | Reject, timeout, 503/unavailable | FAILED | Record exact cause; continue BE |
| FAILED | Enter cooldown | COOLDOWN | No immediate request storm |
| ACTIVE | Lease expiry, release or loss | COOLDOWN | Restore BE; record active duration |
| COOLDOWN | Timer expires | OBSERVE | Eligible for another decision |
| OBSERVE | No request | OBSERVE | Remain on BE |

Implementation must define timer ordering when several events have identical timestamps, request idempotency, cancellation, provider callbacks after timeout, rejected duplicate grants, lease extensions (if later introduced), invalid transition exceptions and over/underflow guards. `ACTIVE` without a grant event is invalid. Activation cannot be instantaneous when configured setup delay is positive.

## 9. Counterfactual network and provider fairness

**Same seed is necessary but not sufficient.** Policies request QoD at different times and may make different numbers of requests. If a mock provider draws one random value per request from the same sequential RNG, policy A's first request may face a different environmental event than policy B's first request even with identical seeds.

The fair comparison protocol therefore:

1. Generates and stores the **same immutable exogenous baseline trace** (network state, traffic demand, target arrival, deadlines, jitter shock events) for all policies.
2. Generates common provider availability/failure conditions **indexed by time or underlying request opportunities**, not consumption order from a policy-specific RNG stream.
3. Uses the same predeclared setup-delay and QoD-gain response function, conditioned on exogenous state. Policies do not access future conditions.
4. Separates each policy's endogenous session effects from the immutable exogenous trace to prevent one run from contaminating another.
5. Records one paired observation per **scenario seed** for metrics, rather than treating correlated ticks as independent samples.
6. Reports fallback behavior under 0% grants, no network benefit, provider timeouts and large setup delays.

Potential interference or feedback between session requests and network congestion can be a **separate experimental model**, not quietly mixed into the non-interference baseline.

## 10. Cost and metric definitions

Synthetic service cost:

```text
service_cost = request_count * request_fee
             + active_seconds * active_second_rate
             + optional_cancel_fee

utility_loss = service_cost
             + deadline_miss_count * miss_penalty
             + optional_false_request_penalty
```

Keep **QoD service cost** distinct from total modeled utility loss. Under Best Effort `service_cost = 0`, but its deadline misses can still contribute to utility loss. This prevents the baseline from being mislabeled zero-cost under every definition.

Compute and retain per scenario and policy:

| Metric | Unit / definition |
|---|---|
| `p50_latency_ms`, `p95_latency_ms`, `p99_latency_ms` | Measured within simulated trace with explicit aggregation policy |
| `deadline_miss_rate` | Missed deadline events / eligible deadline events |
| `late_by_ms` | Positive lateness conditional on miss |
| `request_count`, `accept_count`, `rejection_count` | Counts of session requests and outcomes |
| `active_time_s`, `setup_time_s` | Granted and setup time |
| `service_cost_units`, `utility_loss_units` | Synthetic economic quantities, not provider pricing |
| `wasted_request_rate` | Accepted/requested activation with no defined useful event (precise definition frozen first) |
| `QoD_gain_vs_BE` | Paired improvement on the same scenario seed |
| `fallback_success_rate` | Continued BE operation when requests fail |

Always show latency distribution **and** request/cost burden. Describe whether miss rate is conditioned on all deadlines or only target-present/approaching events.

## 11. Evaluation design, statistics and guardrails

Recommended deterministic scenarios: steady low load; congestion bursts; correlated jitter; approaching time-critical object; false positives/no target; recurring short events; provider 0/50/100% accept; timeouts and 503; setup duration 0/1/3 s; 1× gain (no benefit), 0.67× hypothetical gain and other response models; lease expiry; oscillating policy thresholds; unknown/out-of-distribution conditions.

**Protocol:** fix model/version/weights on development seeds; evaluate on held-out scenario seeds; run all three policies with shared exogenous conditions; compute paired per-seed differences and uncertainty intervals via paired bootstrap when appropriate. Use effect sizes and worst-case seeds; avoid declaring a statistical benefit from a per-tick t-test with autocorrelated observations.

| Test ID | Scenario | Expected engineering invariant |
|---|---|---|
| QOD-01 | Best Effort | `request_count=0`, `service_cost=0` |
| QOD-02 | Static threshold near boundary | Deterministic expected request decision |
| QOD-03 | Adaptive with `target_present=false` | No eligible QoD request |
| QOD-04 | Provider always rejects | Never `ACTIVE`; BE fallback; finite costs |
| QOD-05 | QoD latency factor=1.0 | No modeled direct latency improvement from activation |
| QOD-06 | Long setup delay | No immediate or backdated gain |
| QOD-07 | Same locked scenario with 3 policies | Exact exogenous trace equality + paired seed comparison |
| QOD-08 | Lease expiry, duplicate callback, timeout | FSM coherent; costs and request IDs not double counted |
| QOD-09 | Out-of-order timestamps / malformed rates | Deterministic reject with reason |
| QOD-10 | 30+ independent scenario seeds | Per-seed raw outputs, CI and negative cases preserved |
| QOD-11 | Different request timing under same environmental outcomes | Provider random draw order cannot bias fairness |
| QOD-12 | Adaptive tuning on development seeds | Held-out leakage checks pass |

**Candidate acceptance target** (not a measured promise): adaptive must outperform or establish a documented Pareto trade-off against both baselines in locked conditions without severe worst-seed regressions; maintain proper fallback, bounded request rate and full traceability. Declare the quantitative improvement, confidence level and acceptable cost **before** final held-out evaluation.

## 12. Development and implementation roadmap

| Phase | Deliverables | Exit condition |
|---|---|---|
| Q0 | Freeze schema, metric denominators, causal observability | Design contracts and deterministic event ordering accepted |
| Q1 | Scenario generator + replayable trace | Same seed reproduces external network events |
| Q2 | Three baseline policy interfaces | No future access; deterministic boundary logic |
| Q3 | FSM, mock provider, request IDs and failure paths | No invalid session lifecycle; BE fallback preserved |
| Q4 | QoD response model + cost ledger | Gains/costs attributable and parameterized |
| Q5 | Paired experiment engine + statistics | Scenario-indexed common randomness; no leakage |
| Q6 | CSV/JSON/HTML/SVG audit reporting + local CLI | Reproducibility manifest includes config and hashes |
| Q7 | Stress, packaging and Windows/Linux CI | Resource-bounded, offline behavior documented |
| Q8 | Final scientific acceptance | Honest scope-limited claims based on held-out synthetic evaluation |

Real operator-network experiments, if ever authorized, are a **separately scoped future project**; no need for SIM card, cloud APIs or monthly fees to finish this simulator.


### Architecture freeze — ADR-001 (2026-10-11)

**Delivery sequence is locked:** **(0) GitHub README and architecture freeze → (1) complete and harden the offline backend → (2) build and polish the frontend → (3) complete end-to-end synthetic/system acceptance → (4) perform independent real-data evaluation LAST.** No production/field claims before stage 4. A change to this sequence or the v1 system boundary requires an explicit, documented design revision; a README does not claim the target code already exists.

**Frozen cross-project implementation decisions:**

| Decision | Contract |
|---|---|
| Operating environment | Windows 10/11 first; Linux CI/secondary execution where practical; local CPU operation, no mandatory cloud, subscription, paid API or hosted inference |
| Backend | Python 3.11+ target for new modules; pure domain/application layer stays callable from CLI without an HTTP server; explicit typed schemas and versioned run artifacts |
| API adapter | Optional local FastAPI/Pydantic `v1` adapter only **after the core backend is functional**; bind to `127.0.0.1` by default, never expose the service to the LAN by default |
| Frontend | **Planned, not implemented:** React + TypeScript + Vite, locally bundled static assets, no CDN/telemetry, responsive clear dashboard; Turkish-first labels with traceable units, errors and provenance |
| Integration | Frontend consumes only the versioned local API; simulation/math never runs as an unreviewed duplicate implementation in browser code; shared CLI/API core |
| Storage | Local file-backed runs (`JSON`/`CSV`/`SVG`/`PNG`/`HTML` as appropriate), explicit schema versions, safe output paths and reproducibility manifest; no required database or network service |
| UI truthfulness | Never invent a result, fallback silently, or display a planned feature as operational; quality warnings and `not available` states must be visible |
| Testing cadence | Small unit/contract/integration checks accompany backend and UI development; broad system benchmarks and release acceptance happen after backend and frontend completion; **external real data only in the final evaluation stage** |

**Backend completion gate (before frontend development):** all in-scope domain modules, edge-case and lifecycle handling, reproducible synthetic input generation/replay, CLI, stable typed I/O, audit logging, error codes, API contract design, resource/safety bounds and representative automated integration checks are implemented. A green smoke test alone does not satisfy this gate.

**Frontend completion gate (before final acceptance):** complete navigation and workflows, understandable visualizations and units, responsive layout, form validation, explicit loading/empty/error/unreliable states, keyboard/accessibility checks, result drill-down and file export, full offline operation with local API, and correct display of backend-reported evidence. The UI must never determine scientific validity independently of backend flags.

**Final acceptance gate:** perform integrated synthetic replay, locked comparisons, failure/stress and reproducibility tests on Windows, plus cross-platform checks when relevant. **Only after these steps** introduce independently sourced, permissioned real observations and evaluate quality without silently tuning to the final test set. For the QoD simulator, a real trace is *offline replay evidence*, not proof of live operator QoD gains.

### QoD-PolicyLab frontend contract (planned)

The local interface will provide a **scenario editor** (network load, deadlines, arrival assumptions), **policy comparator** (Best Effort, static and adaptive, with versioned parameters), **session timeline** (FSM transitions and provider grants/denials), **benefit/cost view** (latency distribution, misses, request counts and synthetic costs), and an **evidence explorer** (paired seeds, worst cases, config and exports). All plots show simulated quantities explicitly; they are not real 5G SLAs.

The last real-data stage may replay licensed/anonymized measured latency and jitter traces **offline** to evaluate realism. It does not invoke a carrier QoD API, prove commercial network improvements or require a SIM, account or operator contract. A live-provider integration would be a separately approved scope.

## 13. Repository layout (proposed, not present yet)

```text
QoD-PolicyLab/
├── README.md
├── pyproject.toml
├── src/qodpolicylab/
│   ├── scenario/
│   ├── policies/
│   ├── fsm/
│   ├── provider/
│   ├── network/
│   ├── cost/
│   ├── metrics/
│   ├── report/
│   └── cli.py
├── tests/
├── frontend/            # planned React/TypeScript/Vite offline UI
├── experiments/
├── examples/
├── data/synthetic/
├── docs/
└── .github/workflows/ci.yml
```

## 14. Working backend v0.1 CLI (hypothetical QoD only)

```powershell
py -m pip install -e .
py -m unittest discover -s tests -v
py -m qodpolicylab generate --config examples/demo_config.json --seed 42 --out runs/trace
py -m qodpolicylab simulate --config examples/demo_config.json --trace runs/trace/scenario.jsonl --policy adaptive --out runs/adaptive
py -m qodpolicylab compare --config examples/demo_config.json --seeds 30 --out runs/comparison
py -m qodpolicylab sweep --config examples/demo_config.json --seeds 30 --out runs/sweep
py -m qodpolicylab report --run runs/comparison
```

Implemented outputs include `scenario.jsonl`, `sessions.json`, `network_realization.csv`, `metrics.json`, `paired_trials.csv`, `report.html` and checksum manifests. These are simulated events and costs, **not measured network benefits**. The previous nested design config has been superseded by the flat `1.0` schema in `examples/demo_config.json`.

## 15. Implementation choices, safety and release constraints

**Proposed:** Python ≥3.11, standard-library `dataclasses`, `enum`, `random` or NumPy RNG with explicitly isolated streams, NumPy for vectorized scenarios, pandas optional for export, Matplotlib or dependency-free SVG for plots, `pytest` or `unittest` for tests. Pin exact versions during implementation. Offline-only simulation; no HTTP/socket calls are required in core execution.

Security and data governance: schema validation, bounded scenario sizes, path safety, no accidental provider calls, no secrets in logs, no dangerous serialization, and default synthetic example traces. Third-party traces require legal use and privacy review. Do not identify the project as a validated 5G QoS product or offer guaranteed safety benefits.

**License:** no repository license has been chosen at README stage. Dependency and distribution licenses must be reviewed before public/commercial releases.

## 16. Technical references

- [CAMARA Quality on Demand API project](https://github.com/camaraproject/QualityOnDemand) — conceptual inspiration, **not** proof of integration or operator support
- [CAMARA Quality on Demand API definitions](https://github.com/camaraproject/QualityOnDemand/tree/main/code/API_definitions)
- [NumPy random sampling](https://numpy.org/doc/stable/reference/random/index.html) — reproducible, separated RNG streams

---

**Development principle:** finalize and document the architecture first, implement all planned offline simulator components next, and perform locked acceptance/benchmarking last. Neither a README nor passing synthetic tests implies a measured telecom-network SLA.