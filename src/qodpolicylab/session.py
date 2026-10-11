"""Explicit local QoD session lifecycle with time-indexed provider outcomes."""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import Config


@dataclass
class Session:
    cfg:Config
    state:str='IDLE'
    request_id:int=0
    requests:int=0
    accepts:int=0
    rejects:int=0
    timeouts:int=0
    active_seconds:float=0.
    pending_at:float|None=None
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
        if self.state=='REQUESTING' and t+1e-9>=self.pending_at:
            if self.pending_grant:
                self.accepts+=1;self.active_until=self.pending_at+self.cfg.lease_s
                self._event(t,'GRANT','ACTIVE')
            else:
                self.timeouts+=int(self.pending_failure=='TIMEOUT')
                self.rejects+=int(self.pending_failure!='TIMEOUT')
                self._event(t,self.pending_failure or 'REJECT','FAILED')
            self.pending_at=None
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
        self.request_id+=1;self.requests+=1
        self.pending_at=t+self.cfg.setup_delay_s
        self.pending_grant=provider_u<self.cfg.accept_probability
        self.pending_failure='TIMEOUT' if provider_u < self.cfg.accept_probability+self.cfg.provider_timeout_probability else 'REJECT'
        self._event(t,'REQUEST','REQUESTING')
        if self.cfg.setup_delay_s==0:self.advance(t)

    def account_active(self, tick_s):
        if self.state=='ACTIVE':self.active_seconds+=tick_s