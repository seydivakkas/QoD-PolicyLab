"""Pure-standard-library uncertainty-aware TTC and synthetic QoD policy.

TTC is a constant-velocity radial proxy, NOT an actual collision probability.
"""
from __future__ import annotations
import math


def _vector(x):
    if not isinstance(x,(tuple,list)) or len(x)!=2:return None
    try: a=[float(x[0]),float(x[1])]
    except (TypeError,ValueError):return None
    return a if all(math.isfinite(v) for v in a) else None


def _cov(value):
    try:m=[[float(x) for x in row] for row in value]
    except (ValueError,TypeError):raise ValueError('INVALID_2X2_COVARIANCE')
    if len(m)!=2 or any(len(row)!=2 for row in m) or any(not math.isfinite(x) for row in m for x in row):raise ValueError('INVALID_2X2_COVARIANCE')
    a,b=m[0];c,d=m[1]
    if abs(b-c)>1e-9 or a<-1e-9 or d<-1e-9 or a*d-b*c<-1e-8:raise ValueError('INVALID_2X2_COVARIANCE')
    return m


def _quad(v,M):
    return sum(v[i]*M[i][j]*v[j] for i in range(2) for j in range(2))


def _dot(x,y):return sum(a*b for a,b in zip(x,y))


def compute_ttc_with_uncertainty(pos,vel,cov_pos,cov_vel,*,cross_cov=None,confidence_z=1.645):
    """Time-to-zero-range approximation and first-order delta-method bound.

    cross_cov is Cov(position, velocity). Joint covariance must be PSD.
    When near-zero closing rate, delta approximation is unstable; withhold.
    """
    r=_vector(pos);v=_vector(vel);P=_cov(cov_pos);V=_cov(cov_vel)
    if r is None or v is None:raise ValueError('INVALID_RELATIVE_STATE')
    if isinstance(confidence_z,bool) or not math.isfinite(confidence_z) or confidence_z<0:raise ValueError('INVALID_CONFIDENCE')
    C=[[0.,0.],[0.,0.]] if cross_cov is None else _cov_cross(cross_cov)
    # Test symmetric 4x4 covariance by PSD-preserving LDL with pivot tolerance.
    M=[P[0]+C[0],P[1]+C[1],
       [C[0][0],C[1][0]]+V[0],[C[0][1],C[1][1]]+V[1]]
    if not _is_psd(M):raise ValueError('INVALID_JOINT_COVARIANCE')
    rv=_dot(r,v);d2=_dot(r,r)
    if d2<=1e-12:return {'status':'OVERLAPPING','ttc_s':0.,'ttc_lower_s':0.,'sigma_s':0.}
    if rv>=-1e-9:return {'status':'NON_CLOSING','ttc_s':None,'ttc_lower_s':None,'sigma_s':None}
    T=-d2/rv
    jr=[(-2*r[i]*rv+d2*v[i])/(rv**2) for i in range(2)]
    jv=[d2*r[i]/(rv**2) for i in range(2)]
    variance=_quad(jr,P)+_quad(jv,V)+2*sum(jr[i]*C[i][j]*jv[j] for i in range(2) for j in range(2))
    if variance<-1e-8:raise ValueError('NEGATIVE_TTC_VARIANCE')
    std=math.sqrt(max(0.,variance));lower=max(0.,T-confidence_z*std)
    return {'status':'VALID' if std/max(T,1e-12)<.6 else 'UNCERTAIN_TTC',
            'ttc_s':T,'sigma_s':std,'ttc_lower_s':lower,
            'assumptions':'constant relative velocity, radial approach, one-sided delta bound; NOT physical collision probability'}


def _cov_cross(raw):
    try:c=[[float(x) for x in row] for row in raw]
    except (TypeError,ValueError):raise ValueError('INVALID_CROSS_COVARIANCE')
    if len(c)!=2 or any(len(r)!=2 for r in c) or any(not math.isfinite(x) for r in c for x in r):raise ValueError('INVALID_CROSS_COVARIANCE')
    return c


def _is_psd(mat):
    """Symmetric Jacobi eigenvalue bound for tiny 4x4 matrices."""
    m=[row.copy() for row in mat];n=len(m)
    if any(len(row)!=n for row in m):return False
    for i in range(n):
        for j in range(n):
            if abs(m[i][j]-m[j][i])>1e-8:return False
    for _ in range(65):
        p,q=max(((i,j) for i in range(n) for j in range(i+1,n)),key=lambda ij:abs(m[ij[0]][ij[1]]))
        if abs(m[p][q])<1e-11:break
        angle=.5*math.atan2(2*m[p][q],m[q][q]-m[p][p]);c=math.cos(angle);s=math.sin(angle)
        # Standard Jacobi similarity rotation; n small.
        pp=m[p][p];qq=m[q][q];pq=m[p][q]
        m[p][p]=c*c*pp-2*s*c*pq+s*s*qq
        m[q][q]=s*s*pp+2*s*c*pq+c*c*qq
        m[p][q]=m[q][p]=0.
        for k in range(n):
            if k in (p,q):continue
            a,b=m[k][p],m[k][q]
            m[k][p]=m[p][k]=c*a-s*b
            m[k][q]=m[q][k]=s*a+c*b
    return min(m[i][i] for i in range(n))>=-1e-8


def qos_decision(ttc,*,latency_p99_ms,setup_delay_s=1.,headroom_s=.3,active=False,
                 predicted_qod_factor=.7,service_cost_units=1.,miss_penalty_units=3.,min_gain=0.):
    if ttc['status']=='NON_CLOSING':return {'action':'MAINTAIN_BEST_EFFORT','why':'NON_CLOSING'}
    if ttc['status'] in ('OVERLAPPING','UNCERTAIN_TTC'):
        return {'action':'LOCAL_FAILSAFE_REQUIRED','why':'UNSAFE_TTC_CANNOT_BE_SOLVED_BY_NETWORK'}
    vals=(latency_p99_ms,setup_delay_s,headroom_s,predicted_qod_factor,service_cost_units,miss_penalty_units,min_gain)
    if any(isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or x<0 for x in vals) or predicted_qod_factor>1:raise ValueError('INVALID_QOD_PARAMETERS')
    deadline=max(0.,ttc['ttc_lower_s']-headroom_s)
    baseline=(latency_p99_ms/1000)>deadline
    with_qod=(latency_p99_ms/1000)*predicted_qod_factor>deadline
    if deadline<=setup_delay_s:
        return {'action':'LOCAL_FAILSAFE_REQUIRED','why':'QOD_SETUP_CANNOT_MEET_DEADLINE','deadline_s':deadline}
    gain=miss_penalty_units*int(baseline and not with_qod)-service_cost_units
    if active:return {'action':'MAINTAIN_ACTIVE_QOD','why':'ALREADY_ACTIVE','deadline_s':deadline}
    return {'action':'REQUEST_QOD' if gain>min_gain else 'MAINTAIN_BEST_EFFORT',
            'why':'SYNTHETIC_EXPECTED_UTILITY_PROXY','deadline_s':deadline,'proxy_gain_units':gain,
            'warning':'Cannot replace local emergency response or certify accident avoidance'}


def simulate_pareto(events,*,qod_factor=.7,request_cost=1.,active_cost_per_event=.2):
    """Compare baseline vs adaptive on the SAME synthetic trace, NO accident claims."""
    data=list(events)
    if not data:raise ValueError('EMPTY_EXOGENOUS_TRACE')
    rows={}
    for policy in ('best_effort','adaptive'):
        misses=0;cost=0.;requests=0;out=[]
        for e in data:
            if any(k not in e for k in ('deadline_ms','latency_ms','p99_ms','ttc_lower_s')):raise ValueError('MISSING_EVENT_DATA')
            t={'status':'VALID','ttc_lower_s':min(e['ttc_lower_s'],e['deadline_ms']/1000)}
            action=qos_decision(t,latency_p99_ms=e['p99_ms'],setup_delay_s=e.get('setup_delay_s',.1),
                               headroom_s=0.,service_cost_units=request_cost) if policy=='adaptive' else {'action':'MAINTAIN_BEST_EFFORT'}
            active=action['action']=='REQUEST_QOD';requests+=int(active)
            cost+=(request_cost+active_cost_per_event) if active else 0.
            latency=e['latency_ms']*(qod_factor if active else 1.)
            miss=latency>e['deadline_ms'];misses+=int(miss)
            out.append({'action':action['action'],'deadline_miss':miss,'service_cost_units':cost})
        rows[policy]={'deadline_miss_rate':misses/len(data),'service_cost_units':cost,'requests':requests,'events':out}
    front=[]
    for name,v in rows.items():
        if not any(w['deadline_miss_rate']<=v['deadline_miss_rate'] and w['service_cost_units']<=v['service_cost_units'] and
                   (w['deadline_miss_rate']<v['deadline_miss_rate'] or w['service_cost_units']<v['service_cost_units'])
                   for k,w in rows.items() if k!=name):front.append(name)
    return {'policies':rows,'pareto_frontier':front,'risk_metric':'deadline miss only (not physical collision probability)','model':'synthetic proxy'}
