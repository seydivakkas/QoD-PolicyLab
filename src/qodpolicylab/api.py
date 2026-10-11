"""Version 1.0 offline policy API; all results are hypothetical simulations."""
from __future__ import annotations
from .models import Config
from .scenario import generate
from .simulation import run,compare,POLICIES
from .loopback import create_server


def dispatch(request):
    if not isinstance(request,dict) or set(request)!={'schema_version','operation','input'}:
        raise ValueError('exact JSON API envelope required')
    if request['schema_version']!='1.0' or request['operation'] not in ('simulate','compare'):
        raise ValueError('unsupported API operation/version')
    inp=request['input']
    if not isinstance(inp,dict) or 'config' not in inp:raise ValueError('config required')
    cfg=Config.from_dict(inp['config'])
    if request['operation']=='simulate':
        if set(inp)-{'config','policy','callback_delay_s','request_timeout_s'} or inp.get('policy') not in POLICIES:
            raise ValueError('invalid simulate input')
        res=run(generate(cfg),cfg,inp['policy'],callback_delay_s=inp.get('callback_delay_s'),
                request_timeout_s=inp.get('request_timeout_s'))
        # Keep time series available for client review, but bound by Config max ticks.
        return res
    if set(inp)-{'config','seeds'}:
        raise ValueError('invalid comparison input')
    seeds=inp.get('seeds',10)
    if type(seeds) is not int or not 1<=seeds<=50:
        raise ValueError('API caps comparisons to 50 seeds')
    return compare(cfg,seeds=seeds)


def server(*,token,port=0):
    return create_server(dispatch,token=token,port=port)