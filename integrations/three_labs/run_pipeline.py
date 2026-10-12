"""Run three local stdio stages, preserving separation and nonzero errors.
Call after editable installs: KalmanTrackLab, BEV-MotionLab, QoD-PolicyLab.
"""
from __future__ import annotations
import argparse,os,subprocess,sys,json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--frames',type=int,default=120)
    p.add_argument('--out',default='simulation-telemetry.jsonl');a=p.parse_args()
    if not 10<=a.frames<=10000:raise ValueError('INVALID_FRAMES')
    py=sys.executable
    root=Path(__file__).resolve().parent
    # Pipe subprocesses without shell; stderr remains visible for debugging.
    producer=subprocess.Popen([py,str(root/'driver'/'synthetic_driver.py'),'--frames',str(a.frames)],stdout=subprocess.PIPE)
    kalman=subprocess.Popen([py,'-m','kalmantracklab.telemetry_stage'],stdin=producer.stdout,stdout=subprocess.PIPE)
    producer.stdout.close()
    bev=subprocess.Popen([py,'-m','bevmotionlab.telemetry_stage'],stdin=kalman.stdout,stdout=subprocess.PIPE)
    kalman.stdout.close()
    qod=subprocess.Popen([py,'-m','qodpolicylab.telemetry_stage'],stdin=bev.stdout,stdout=subprocess.PIPE)
    bev.stdout.close()
    path=Path(a.out)
    if path.exists():raise FileExistsError('OUTPUT_EXISTS')
    count=0;error=0
    with path.open('w',encoding='utf-8') as output:
        for raw in qod.stdout:
            obj=json.loads(raw)
            if obj.get('type')=='error':error+=1
            if obj.get('type')=='telemetry':count+=1
            output.write(json.dumps(obj,ensure_ascii=False)+'\n')
    results=[p.wait() for p in (producer,kalman,bev,qod)]
    report={'frames':count,'error_messages':error,'returncodes':results,'output':str(path),
            'source':'SYNTHETIC','acceptance':'NOT_A_FINAL_GATE'}
    print(json.dumps(report))
    if count!=a.frames or error or any(results):raise SystemExit(1)

if __name__=='__main__':main()
