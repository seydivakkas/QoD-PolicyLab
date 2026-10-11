"""Deterministic asynchronous mock-provider callback queue.

Callbacks are scheduled from the *current* request's exogenous provider draw.
No access to future network observations or policy decisions is required.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import heapq
import math

OUTCOMES=('GRANT','TIMEOUT','SERVICE_UNAVAILABLE','REJECT')


@dataclass
class ProviderEventQueue:
    _heap:list=field(default_factory=list,repr=False)
    _counter:int=0
    audit:list=field(default_factory=list)

    def schedule(self, *, request_id, now_s, ready_at_s, outcome):
        if type(request_id) is not int or request_id < 1 or outcome not in OUTCOMES:
            raise ValueError('invalid provider event')
        if any(not math.isfinite(x) for x in (now_s,ready_at_s)) or ready_at_s < now_s:
            raise ValueError('callback cannot be scheduled in the past')
        self._counter += 1
        heapq.heappush(self._heap,(float(ready_at_s),self._counter,request_id,outcome))

    def deliver_through(self, now_s, session):
        if not math.isfinite(now_s) or now_s < 0:
            raise ValueError('delivery clock must be finite and nonnegative')
        while self._heap and self._heap[0][0] <= now_s + 1e-10:
            at,_,request_id,outcome = heapq.heappop(self._heap)
            # Timeouts, lease expiry and cooldown are processed chronologically;
            # no delayed grant can backdate an ACTIVE interval.
            session.advance(at)
            status=session.provider_callback(at,request_id,outcome)
            self.audit.append({'t_s':at,'request_id':request_id,'outcome':outcome,'delivery_status':status})

    def pending_count(self):
        return len(self._heap)