"""Offline CLI; JSONL trace replay and policy comparison, no network required."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from dataclasses import asdict
from .models import Config
from .scenario import generate,read_trace,write_trace
from .simulation import run,compare,POLICIES
from .report import render_report


def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def manifest(folder,names):
    save(Path(folder)/'manifest.json',{'schema_version':'1.0','sha256':{name:hashlib.sha256((Path(folder)/name).read_bytes()).hexdigest() for name in names}})


def cfg_from(path,seed_override=None):
    obj=json.loads(Path(path).read_text(encoding='utf-8')) if path else {}
    if 'provider' in obj or 'network' in obj or 'cost' in obj:
        raise ValueError('nested design-only config is not supported; use flat 1.0 config fields')
    if seed_override is not None:obj['seed']=seed_override
    return Config.from_dict(obj)


def main(argv=None):
    p=argparse.ArgumentParser(description='Offline QoD policy engine (synthetic-only)')
    sp=p.add_subparsers(dest='cmd',required=True)
    g=sp.add_parser('generate');g.add_argument('--config');g.add_argument('--seed',type=int);g.add_argument('--out',required=True)
    s=sp.add_parser('simulate');s.add_argument('--config');s.add_argument('--trace',required=True);s.add_argument('--policy',choices=POLICIES,required=True);s.add_argument('--out',required=True)
    c=sp.add_parser('compare');c.add_argument('--config');c.add_argument('--seeds',type=int,default=30);c.add_argument('--out',required=True)
    r=sp.add_parser('report');r.add_argument('--run',required=True);r.add_argument('--out')
    args=p.parse_args(argv)
    if args.cmd=='report':
        print(json.dumps({'report':str(render_report(args.run,args.out))}));return
    cfg=cfg_from(getattr(args,'config',None),getattr(args,'seed',None))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    if args.cmd=='generate':
        write_trace(generate(cfg),out/'scenario.jsonl');save(out/'config.json',asdict(cfg));manifest(out,['scenario.jsonl','config.json'])
        answer={'trace':str(out/'scenario.jsonl')}
    elif args.cmd=='simulate':
        trace=read_trace(args.trace)
        res=run(trace,cfg,args.policy)
        rows=res.pop('rows');events=res.pop('sessions')
        save(out/'metrics.json',res);save(out/'sessions.json',events);save(out/'config.json',asdict(cfg))
        with (out/'network_realization.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        manifest(out,['metrics.json','sessions.json','network_realization.csv','config.json'])
        answer={'output':str(out),'policy':args.policy,'requests':res['request_count']}
    else:
        res=compare(cfg,args.seeds);trials=res.pop('paired_trials')
        save(out/'metrics.json',res);save(out/'config.json',asdict(cfg))
        with (out/'paired_trials.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(trials[0]));w.writeheader();w.writerows(trials)
        manifest(out,['metrics.json','config.json','paired_trials.csv'])
        answer={'output':str(out),'seeds':args.seeds}
    print(json.dumps(answer,sort_keys=True))

if __name__=='__main__':main()