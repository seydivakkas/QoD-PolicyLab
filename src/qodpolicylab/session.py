"""Explicit local QoD session lifecycle with time-indexed provider outcomes."""
from __future__ import annotations
from dataclasses import dataclass, field
import math
from .models import Config


@dataclass
class Session:
    cfg:Config
    auto_provider:bool=True
    request_timeout_s:float|None=None
    state:str='IDLE'
    request_id:int=0
    requests:int=0
    accepts:int=0
    rejects:int=0
    timeouts:int=0
    service_unavailable:int=0
    _resolved_ids:set[int]=field(default_factory=set,repr=False)
    active_seconds:float=0.
    pending_at:float|None=None
    timeout_at:float|None=None
    active_until:float|None=None
    cooldown_until:float|None=None
    pending_grant:bool=False
    pending_failure:str|None=None
    events:list=field(default_factory=list)

    def _event(self,t,event,state):
        self.events.append({'t_s':t,'event':event,'state':state,'request_id':self.request_id})
        self.state=state

    def advance(self,t):
        """Process expired timers before decision, with no backdated benefit."""
        if self.state=='IDLE':self._event(t,'START','OBSERVE')
        if self.state=='REQUESTING':
            if self.auto_provider and t+1e-9>=self.pending_at:
                outcome='GRANT' if self.pending_grant else (self.pending_failure or 'REJECT')
                self.provider_callback(t, self.request_id, outcome)
            elif not self.auto_provider and self.timeout_at is not None and t+1e-9>=self.timeout_at:
                # Apply at the timeout instant, not the next coarse simulation tick.
                self.provider_callback(self.timeout_at,self.request_id,'TIMEOUT')
        if self.state=='ACTIVE' and t+1e-9>=self.active_until:
            self._event(t,'LEASE_EXPIRED','COOLDOWN')
            self.cooldown_until=t+self.cfg.cooldown_s
        if self.state=='FAILED':
            self._event(t,'FAILURE_FALLBACK','COOLDOWN')
            self.cooldown_until=t+self.cfg.cooldown_s
        if self.state=='COOLDOWN' and t+1e-9>=self.cooldown_until:
            self._event(t,'COOLDOWN_END','OBSERVE')

    def request(self,t,provider_u):
        if self.state!='OBSERVE':raise ValueError('request only allowed from OBSERVE')
        if not math.isfinite(provider_u) or not 0 <= provider_u <= 1:
            raise ValueError('provider draw must be finite and within [0,1]')
        self.request_id+=1;self.requests+=1
        self.pending_at=t+self.cfg.setup_delay_s
        if not self.auto_provider:
            if self.request_timeout_s is None or not math.isfinite(self.request_timeout_s) or self.request_timeout_s <= 0:
                raise ValueError('external callbacks require positive finite request_timeout_s')
            self.timeout_at=t+self.request_timeout_s
        self.pending_grant=provider_u<self.cfg.accept_probability
        if provider_u < self.cfg.accept_probability+self.cfg.provider_timeout_probability:
            self.pending_failure='TIMEOUT'
        elif provider_u < (self.cfg.accept_probability+self.cfg.provider_timeout_probability+
                           self.cfg.provider_service_unavailable_probability):
            self.pending_failure='SERVICE_UNAVAILABLE'
        else:
            self.pending_failure='REJECT'
        self._event(t,'REQUEST','REQUESTING')
        if self.cfg.setup_delay_s==0 and self.auto_provider:self.advance(t)

    def provider_callback(self, t: float, request_id: int, outcome: str) -> str:
        """Idempotent correlated callback. Never resurrects expired or replaced IDs.

        The deterministic provider calls this after setup; external injectors may
        replay a message, but cannot attach it to a different request.
        """
        if not math.isfinite(t) or t < 0:
            raise ValueError('callback time must be finite and nonnegative')
        if type(request_id) is not int or request_id <= 0 or request_id > self.request_id:
            raise ValueError('invalid future/unknown provider request ID')
        if outcome not in ('GRANT','REJECT','TIMEOUT','SERVICE_UNAVAILABLE'):
            raise ValueError('invalid provider outcome')
        if request_id in self._resolved_ids:
            return 'IGNORED_DUPLICATE'
        if self.state != 'REQUESTING' or request_id != self.request_id:
            return 'IGNORED_STALE'
        if outcome != 'TIMEOUT' and (self.pending_at is None or t+1e-9 < self.pending_at):
            raise ValueError('callback cannot precede the modeled setup delay')
        self._resolved_ids.add(request_id)
        if outcome == 'GRANT':
            self.accepts += 1
            # Use actual callback time: a late response cannot claim earlier benefit.
            self.active_until = t + self.cfg.lease_s
            self._event(t, 'GRANT', 'ACTIVE')
        else:
            self.rejects += int(outcome == 'REJECT')
            self.timeouts += int(outcome == 'TIMEOUT')
            self.service_unavailable += int(outcome == 'SERVICE_UNAVAILABLE')
            self._event(t, outcome, 'FAILED')
        self.pending_at = None
        self.timeout_at = None
        self.pending_failure = None
        return 'APPLIED'

    def account_active(self, tick_s):
        if self.state=='ACTIVE':self.active_seconds+=tick_s