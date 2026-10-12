"""Deterministic, opt-in transient provider retry/backoff guard (not carrier integration)."""
from dataclasses import dataclass,field
import math

@dataclass(frozen=True)
class RetryConfig:
    max_requests:int=3
    max_transient_failures:int=2
    initial_delay_s:float=1.
    factor:float=2.
    max_delay_s:float=8.
    def __post_init__(self):
        if type(self.max_requests) is not int or not 1<=self.max_requests<=1000:
            raise ValueError('RETRY_INVALID_REQUEST_BUDGET')
        if type(self.max_transient_failures) is not int or not 0<=self.max_transient_failures<=1000:
            raise ValueError('RETRY_INVALID_FAILURE_BUDGET')
        for name in ('initial_delay_s','factor','max_delay_s'):
            v=getattr(self,name)
            if type(v) not in (int,float) or not math.isfinite(v) or v<=0:
                raise ValueError('RETRY_INVALID_'+name.upper())
        if self.factor<1 or self.initial_delay_s>self.max_delay_s:
            raise ValueError('RETRY_INVALID_BACKOFF')

@dataclass
class RetryGuard:
    config:RetryConfig
    next_allowed_s:float=0.
    transient_failures:int=0
    permanently_denied:bool=False
    _cursor:int=field(default=0,repr=False)
    audit:list=field(default_factory=list)
    def observe(self,session):
        if len(session.events)<self._cursor:
            raise ValueError('RETRY_EVENT_LOG_TRUNCATED')
        for event in session.events[self._cursor:]:
            name=event['event'];at=event['t_s']
            if not math.isfinite(at) or at<0:
                raise ValueError('RETRY_INVALID_EVENT_TIME')
            if name=='GRANT':
                self.transient_failures=0
                self.next_allowed_s=at
            elif name in ('TIMEOUT','SERVICE_UNAVAILABLE'):
                self.transient_failures+=1
                exponent=self.transient_failures-1
                threshold=(math.log(self.config.max_delay_s/self.config.initial_delay_s)/
                           math.log(self.config.factor)) if self.config.factor>1 else math.inf
                delay=(self.config.max_delay_s if exponent>=threshold else
                       min(self.config.max_delay_s,
                           self.config.initial_delay_s*self.config.factor**exponent))
                self.next_allowed_s=max(self.next_allowed_s,at+delay)
                self.audit.append({'request_id':event['request_id'],'outcome':name,
                                   'at_s':at,'retry_after_s':self.next_allowed_s})
            elif name=='REJECT':
                self.permanently_denied=True
                self.audit.append({'request_id':event['request_id'],'outcome':'REJECT',
                                   'at_s':at,'retry_after_s':None})
            elif name=='CANCEL':
                self.permanently_denied=True
        self._cursor=len(session.events)
    def allowed(self,session,now_s):
        if not math.isfinite(now_s) or now_s<0:
            raise ValueError('RETRY_INVALID_NOW')
        return bool(session.state=='OBSERVE' and
                    session.requests<self.config.max_requests and
                    self.transient_failures<=self.config.max_transient_failures and
                    not self.permanently_denied and now_s+1e-12>=self.next_allowed_s)
    def snapshot(self,session):
        return {'allowed_next_request':self.allowed(session,max(0.,getattr(session,'_clock_s',0.) or 0.)),
                'requests':session.requests,'failure_count':self.transient_failures,
                'retry_after_s':self.next_allowed_s,
                'permanently_denied':self.permanently_denied,
                'max_requests':self.config.max_requests,
                'audit':list(self.audit),'provider_authorization_real':False}
