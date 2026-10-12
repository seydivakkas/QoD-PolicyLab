# QoD-PolicyLab v0.1.8 opt-in kinematic deadline signal

- `ttc_policy`: analytic first-order delta variance for a constant-relative-velocity radial TTC proxy and explicit nonclosing/uncertain cases. It does NOT calculate a calibrated collision probability or account for full vehicle extents, acceleration, multimodal occupancy, systematic uncertainty, driver response or braking physics.
- `qos_decision`: conservative deadline margin, modeled p99 synthetic latency, setup feasibility, explicit LOCAL_FAILSAFE_REQUIRED **warning**; no physical actuator interface or automatic braking.
- `simulate_pareto`: Best Effort / Adaptive using identical synthetic external event input; reports **deadline miss proxy**, not accident rate. There is no evidence that requesting QoD prevents collisions.
- `telemetry_stage`: JSONL downstream demo; its ACTIVE_MOCK state is a simplified visual-only stand-in and is not the complete accepted provider FSM. No operator API calls occur.
- `integrations/three_labs`: optional shared live React/WebSocket **development demo**; independent Kalman and BEV repos remain the source of truth for their separate engineering layers. No final release acceptance.

**Backend v1 still HOLD**: frozen independent synthetic utility guardrails, resource performance, proper correlated covariance and full event model are not yet accepted. No real data, no external provider, no safety-critical deployment.
