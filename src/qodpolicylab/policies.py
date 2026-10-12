"""Causal policy strategies; no simulation outcomes or provider draws exposed."""
from __future__ import annotations
from .models import Config, PolicyView


def eligible(obs: PolicyView):
    return obs.target_present and obs.approaching


def decide(policy, obs: PolicyView, cfg: Config):
    if policy not in ('best_effort','static','adaptive'):
        raise ValueError('unknown policy')
    if policy=='best_effort' or not eligible(obs):return False
    if policy=='static':return obs.severity >= cfg.static_threshold
    # Transparent heuristic, not an empirically calibrated predictor.
    # Demand is evaluated at the current observation; higher uncertainty reduces benefit.
    excess=max(0.,obs.latency_ms-obs.deadline_ms)/max(obs.deadline_ms,1.)
    urgency=min(1.,excess+obs.jitter_ms/max(obs.deadline_ms,1.))
    benefit=obs.severity*urgency*(1.-obs.uncertainty)*cfg.accept_probability
    return benefit > cfg.adaptive_gate