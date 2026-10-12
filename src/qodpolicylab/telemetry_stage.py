"""QoD stream stage: BEV metre-space states -> synthetic policy telemetry.
No real network activation and no real automotive emergency intervention.
"""
from __future__ import annotations
import json,sys,math
from .ttc_policy import compute_ttc_with_uncertainty,qos_decision


def main():
    active_until=0.;requests=0;cost=0.;last=None
    for line in sys.stdin:
        if not line.strip():continue
        try:
            ev=json.loads(line)
            if ev.get('type')!='bev':
                print(json.dumps(ev),flush=True);continue
            t=float(ev['timestamp_s']);dt=max(0,t-last) if last is not None else 0;last=t
            if t<active_until:cost+=.2*dt
            active=t<active_until
            tracks=[];best_action='MAINTAIN_BEST_EFFORT';worst_ttc=None
            for tr in ev['tracks']:
                if not tr['valid']:
                    tracks.append({**tr,'ttc':None,'action':'WITHHELD_INVALID_PROJECTION'});continue
                p=tr['projection'];r=[32-p['x_m'],-p['y_m']]
                v=[-float(tr['velocity_mps'][0]),-float(tr['velocity_mps'][1])]
                ttc=compute_ttc_with_uncertainty(r,v,p['covariance_m2'],tr['velocity_covariance'])
                action=qos_decision(ttc,latency_p99_ms=300,setup_delay_s=.3,headroom_s=.3,
                                    active=active,service_cost_units=1.,miss_penalty_units=3.)
                if action['action']=='REQUEST_QOD' and not active:
                    # Mock accepted instantly for visual DEMO only; must not be
                    # conflated with the real-provider FSM used for policy tests.
                    requests+=1;cost+=1.;active_until=t+3.;active=True
                if action['action']=='LOCAL_FAILSAFE_REQUIRED':best_action=action['action']
                elif best_action=='MAINTAIN_BEST_EFFORT':best_action=action['action']
                if ttc['ttc_lower_s'] is not None:
                    worst_ttc=ttc['ttc_lower_s'] if worst_ttc is None else min(worst_ttc,ttc['ttc_lower_s'])
                tracks.append({**tr,'ttc':ttc,'action':action['action']})
            response={'schema_version':'1.0','type':'telemetry','stage':'qod','timestamp_s':t,
                      'tracks':tracks,'ttc_lower_s':worst_ttc,'action':best_action,
                      'service_cost_units':round(cost,4),'request_count':requests,
                      'session_state':'ACTIVE_MOCK' if active else 'BEST_EFFORT',
                      'latency_margin_ms':None if worst_ttc is None else round(1000*worst_ttc-300,2),
                      'source':'SYNTHETIC','safety_notice':'DEMO ONLY: No real networking or automatic braking'}
            print(json.dumps(response,allow_nan=False),flush=True)
        except Exception as e:
            print(json.dumps({'schema_version':'1.0','type':'error','stage':'qod','error':type(e).__name__,'detail':str(e)}),flush=True)

if __name__=='__main__':main()
