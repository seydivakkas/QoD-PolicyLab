"""Deterministic synthetic frame source. Never uses external/real data."""
from __future__ import annotations
import argparse,json,sys
import numpy as np

def frames(seed=42,n=160,fps=20):
    rng=np.random.default_rng(seed)
    for i in range(n):
        t=i/fps;d=[]
        for k in range(3):
            if (i//25)%5==3 and k==1:continue
            u=90+20*k+(26-3*k)*t
            v=140+k*50+6*np.sin(t*(1+k*.22))
            xy=rng.normal([u,v],[.6,.6])
            d.append({'u':float(xy[0]),'v':float(xy[1]),'confidence':.96})
        yield {'schema_version':'1.0','type':'frame','source':'SYNTHETIC','frame':i,'timestamp_s':t,'detections':d}

def main():
    a=argparse.ArgumentParser();a.add_argument('--seed',type=int,default=42);a.add_argument('--frames',type=int,default=160);a.add_argument('--fps',type=float,default=20);c=a.parse_args()
    for e in frames(seed=c.seed,n=c.frames,fps=c.fps):
        print(json.dumps(e),flush=True)
if __name__=='__main__':main()
