"""Conservative kinematic TTC signal and a mock QoD decision policy.
TTC lower-bound is an approximation and must never be called collision risk.
"""
from __future__ import annotations
import math
import numpy as np


def _cov(x):
    m=np.asarray(x,dtype=float)
    if m.shape!=(2,2) or not np.isfinite(m).all() or not np.allclose(m,m.T,atol=1e-9) or np.linalg.eigvalsh(m).min()<-1e-9:raise ValueError('INVALID_2X2_COVARIANCE')
    return m


def compute_ttc_with_uncertainty(pos,vel,cov_pos,cov_vel,*,cross_cov=None,confidence_z=1.645):
    """Time to zero RANGE under constant radial approach approximation.
    Better geometric collision predictors must consider object extents,
    closest point of approach, acceleration and correlated uncertainty.
    """
    r=np.asarray(pos,float);v=np.asarray(vel,float);P=_cov(cov_pos);V=_cov(cov_vel)
    if r.shape!=(2,) or v.shape!=(2,) or not np.isfinite(r).all() or not np.isfinite(v).all():raise ValueError('INVALID_RELATIVE_STATE')
    rv=float(r@v);d2=float(r@r)
    if d2<=1e-12:return {'status':'OVERLAPPING','ttc_s':0.,'ttc_lower_s':0.,'sigma_s':0.}
    if rv>=-1e-9:return {'status':'NON_CLOSING','ttc_s':None,'ttc_lower_s':None,'sigma_s':None}
    T=-d2/rv
    Jr=(-2*r*rv+d2*v)/(rv*rv)
    Jv=d2*r/(rv*rv)
    C=np.zeros((2,2)) if cross_cov is None else np.asarray(cross_cov,float)
    if C.shape!=(2,2) or not np.isfinite(C).all():raise ValueError('INVALID_CROSS_COVARIANCE')
    joint=np.block([[P,C],[C.T,V]])
    if np.linalg.eigvalsh((joint+joint.T)/2).min()<-1e-8:raise ValueError('INVALID_JOINT_COVARIANCE')
    jac=np.r_[Jr,Jv];var=max(0.,float(jac@joint@jac))
    std=math.sqrt(var);lower=max(0.,T-confidence_z*std)
    return {'status':'VALID' if std/T<.6 else 'UNCERTAIN_TTC',
            'ttc_s':float(T),'sigma_s':std,'ttc_lower_s':float(lower),
            'assumptions':'constant relative velocity; radial-closing approximation; 1-sided normal delta lower bound; NOT a collision probability'}


def qos_decision(ttc,*,latency_p99_ms,setup_delay_s=1.,headroom_s=.3,active=False,
                 predicted_qod_factor=.7,service_cost_units=1.,miss_penalty_units=3.,min_gain=0.):
    if ttc['status'] in ('NON_CLOSING',):return {'action':'MAINTAIN_BEST_EFFORT','why':'NON_CLOSING'}
    if ttc['status'] in ('OVERLAPPING','UNCERTAIN_TTC'):
        return {'action':'LOCAL_FAILSAFE_REQUIRED','why':'UNSAFE_TTC_CANNOT_BE_SOLVED_BY_NETWORK'}
    vals=[latency_p99_ms,setup_delay_s,headroom_s,predicted_qod_factor,service_cost_units,miss_penalty_units]
    if not np.isfinite(vals).all() or min(vals)<0 or predicted_qod_factor>1:raise ValueError('INVALID_QOD_PARAMETERS')
    deadline=max(0.,ttc['ttc_lower_s']-headroom_s)
    baseline=(latency_p99_ms/1000)>deadline
    with_qod=(latency_p99_ms/1000)*predicted_qod_factor>deadline
    if deadline<=setup_delay_s or deadline<=0:
        return {'action':'LOCAL_FAILSAFE_REQUIRED','why':'QOD_SETUP_CANNOT_MEET_DEADLINE','deadline_s':deadline}
    gain=miss_penalty_units*int(baseline and not with_qod)-service_cost_units
    if active:return {'action':'MAINTAIN_ACTIVE_QOD','why':'ALREADY_ACTIVE','deadline_s':deadline}
    return {'action':'REQUEST_QOD' if gain>min_gain else 'MAINTAIN_BEST_EFFORT',
            'why':'SYNTHETIC_EXPECTED_UTILITY_PROXY','deadline_s':deadline,'proxy_gain_units':gain,
            'warning':'Cannot replace local emergency response or certify accident avoidance'}


def simulate_pareto(events,*,qod_factor=.7,request_cost=1.,active_cost_per_event=.2):
    """Shared exogenous synthetic events, compare deadline-miss PROXY, not accident rate."""
    data=list(events)
    if not data:raise ValueError('EMPTY_EXOGENOUS_TRACE')
    rows={}
    for policy in ('best_effort','adaptive'):
        misses=0;cost=0.;requests=0;out=[]
        for e in data:
            if any(k not in e for k in ('deadline_ms','latency_ms','p99_ms','ttc_lower_s')):raise ValueError('MISSING_EVENT_DATA')
            t={'status':'VALID','ttc_lower_s':min(e['ttc_lower_s'],e['deadline_ms']/1000)}
            action=qos_decision(t,latency_p99_ms=e['p99_ms'],setup_delay_s=e.get('setup_delay_s',.1),
                               headroom_s=.0,service_cost_units=request_cost) if policy=='adaptive' else {'action':'MAINTAIN_BEST_EFFORT'}
            active=action['action']=='REQUEST_QOD';requests+=int(active)
            cost+=(request_cost+active_cost_per_event) if active else 0.
            latency=e['latency_ms']*(qod_factor if active else 1.)
            miss=latency>e['deadline_ms'];misses+=int(miss)
            out.append({'action':action['action'],'deadline_miss':miss,'service_cost_units':cost})
        rows[policy]={'deadline_miss_rate':misses/len(data) if data else None,
                      'service_cost_units':cost,'requests':requests,'events':out}
    front=[]
    for name,v in rows.items():
        if not any(w['deadline_miss_rate']<=v['deadline_miss_rate'] and w['service_cost_units']<=v['service_cost_units'] and
                   (w['deadline_miss_rate']<v['deadline_miss_rate'] or w['service_cost_units']<v['service_cost_units'])
                   for k,w in rows.items() if k!=name):front.append(name)
    return {'policies':rows,'pareto_frontier':front,'risk_metric':'deadline miss only (not physical collision probability)','model':'synthetic proxy'}
