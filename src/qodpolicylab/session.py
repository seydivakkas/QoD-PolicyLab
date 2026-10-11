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
    _clock_s:float|None=field(default=None,repr=False)
    request_id:int=0
    requests:int=0
    accepts:int=0
    rejects:int=0
    timeouts:int=0
    service_unavailable:int=0
    _resolved_ids:set[int]=field(default_factory=set,repr=False)
    _cancelled_ids:set[int]=field(default_factory=set,repr=False)
    _renewal_tokens:set[str]=field(default_factory=set,repr=False)
    renewals:int=0
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
        """Advance causally and timestamp timer transitions at their deadlines.

        Coarse observation steps must not shift a lease expiry or cooldown.
        Callbacks after the timeout are stale, regardless of tick resolution.
        """
        if not math.isfinite(t) or t < 0:
            raise ValueError('session clock must be finite and nonnegative')
        if self._clock_s is not None and t < self._clock_s - 1e-9:
            raise ValueError('session clock cannot move backwards')
        if self.state == 'IDLE':
            self._event(t,'START','OBSERVE')
        # Each iteration consumes one state transition, with no temporal jumps.
        for _ in range(8):
            if self.state == 'REQUESTING':
                if self.auto_provider and self.pending_at is not None and t+1e-9 >= self.pending_at:
                    at=self.pending_at
                    outcome='GRANT' if self.pending_grant else (self.pending_failure or 'REJECT')
                    self.provider_callback(at,self.request_id,outcome)
                    continue
                if not self.auto_provider and self.timeout_at is not None and t+1e-9 >= self.timeout_at:
                    self.provider_callback(self.timeout_at,self.request_id,'TIMEOUT')
                    continue
            if self.state == 'ACTIVE' and self.active_until is not None and t+1e-9 >= self.active_until:
                at=self.active_until
                self._event(at,'LEASE_EXPIRED','COOLDOWN')
                self.cooldown_until=at+self.cfg.cooldown_s
                continue
            if self.state == 'FAILED':
                at=self.events[-1]['t_s']
                self._event(at,'FAILURE_FALLBACK','COOLDOWN')
                self.cooldown_until=at+self.cfg.cooldown_s
                continue
            if self.state == 'COOLDOWN' and self.cooldown_until is not None and t+1e-9 >= self.cooldown_until:
                self._event(self.cooldown_until,'COOLDOWN_END','OBSERVE')
                continue
            break
        else:
            raise RuntimeError('session timer did not converge')
        self._clock_s=t

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

    def cancel(self, t: float, request_id: int) -> str:
        """Explicit user/policy cancel with causal cooldown; no resurrection.

        Timers at or before ``t`` are processed before cancellation. An ACTIVE
        interval must not receive QoD gain after the effective cancellation.
        """
        if type(request_id) is not int or request_id <= 0:
            raise ValueError('CANCEL_INVALID_REQUEST_ID')
        self.advance(t)
        if request_id in self._cancelled_ids:
            return 'IGNORED_DUPLICATE'
        if request_id != self.request_id:
            return 'IGNORED_STALE'
        if self.state not in ('REQUESTING','ACTIVE'):
            return 'IGNORED_INACTIVE'
        self._cancelled_ids.add(request_id)
        self._resolved_ids.add(request_id)
        self.pending_at = None
        self.timeout_at = None
        self.pending_failure = None
        self.pending_grant = False
        self.active_until = None
        self.cooldown_until = t + self.cfg.cooldown_s
        self._event(t, 'CANCEL', 'COOLDOWN')
        return 'APPLIED'

    def renew(self, t: float, request_id: int, *, token: str,
              extension_s: float, max_renewals: int = 2) -> str:
        """Bounded idempotent lease extension, no retroactive active time.

        Provider renewal *authorization* is modeled as an already-supplied
        success; real callback/rejection, request billing and retries remain
        separate unimplemented operator integration details.
        """
        if type(request_id) is not int or request_id <= 0:
            raise ValueError('RENEW_INVALID_REQUEST_ID')
        if not isinstance(token, str) or not 1 <= len(token) <= 128:
            raise ValueError('RENEW_INVALID_TOKEN')
        if isinstance(extension_s,bool) or not isinstance(extension_s,(int,float)) or not math.isfinite(extension_s) or not 0 < extension_s <= self.cfg.lease_s:
            raise ValueError('RENEW_INVALID_EXTENSION')
        if type(max_renewals) is not int or not 1 <= max_renewals <= 100:
            raise ValueError('RENEW_INVALID_BUDGET')
        self.advance(t)
        if token in self._renewal_tokens:
            return 'IGNORED_DUPLICATE'
        if request_id != self.request_id or self.state != 'ACTIVE':
            return 'IGNORED_STALE'
        if self.renewals >= max_renewals:
            return 'BUDGET_EXHAUSTED'
        self._renewal_tokens.add(token)
        self.renewals += 1
        self.active_until += extension_s
        self._event(t, 'RENEW', 'ACTIVE')
        return 'APPLIED'

    def account_active(self, tick_s):
        if not math.isfinite(tick_s) or tick_s < 0:
            raise ValueError('active accounting time must be finite and nonnegative')
        if self.state=='ACTIVE':self.active_seconds+=tick_s