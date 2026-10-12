"""Localhost-only demo WebSocket telemetry hub over three JSONL processes.

Requires all three editable Python packages installed. No cloud, real cameras,
real QoD API or external network access. For research demonstrations only.
"""
from __future__ import annotations
import asyncio,json,os,sys
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from driver.synthetic_driver import frames

app=FastAPI(title='Three Labs - synthetic local telemetry',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_credentials=False,allow_methods=['GET'],allow_headers=['*'])


class Hub:
    def __init__(self):
        self.clients=set();self.tasks=[];self.processes=[];self.running=False;self.writer_lock=asyncio.Lock()
        self.counters={'frames':0,'invalid_outputs':0}
    async def broadcast(self,data):
        for w in list(self.clients):
            try:await w.send_json(data)
            except Exception:self.clients.discard(w)
    async def start(self):
        if self.running:return
        self.running=True
        py=sys.executable
        names=('kalmantracklab.telemetry_stage','bevmotionlab.telemetry_stage','qodpolicylab.telemetry_stage')
        try:
            for name in names:
                p=await asyncio.create_subprocess_exec(py,'-m',name,stdin=asyncio.subprocess.PIPE,
                                                         stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
                                                         limit=65536)
                self.processes.append(p)
            self.tasks=[asyncio.create_task(self.relay(self.processes[0],self.processes[1])),
                        asyncio.create_task(self.relay(self.processes[1],self.processes[2])),
                        asyncio.create_task(self.consume()),asyncio.create_task(self.feed())]
            for name,p in zip(names,self.processes):self.tasks.append(asyncio.create_task(self.read_stderr(name,p)))
        except Exception:
            await self.stop();raise
    async def write(self,event):
        if not self.running:return
        async with self.writer_lock:
            self.processes[0].stdin.write((json.dumps(event,allow_nan=False)+'\n').encode())
            await self.processes[0].stdin.drain()
    async def feed(self):
        i=0
        try:
            while self.running:
                for obj in frames(seed=42,n=240,fps=20):
                    if not self.running:return
                    obj['timestamp_s']+=i*12
                    await self.write(obj)
                    self.counters['frames']+=1
                    await asyncio.sleep(.05)
                i+=1
        except (asyncio.CancelledError,BrokenPipeError):return
    async def relay(self,src,dst):
        try:
            while self.running:
                raw=await src.stdout.readline()
                if not raw:break
                dst.stdin.write(raw);await dst.stdin.drain()
        except (asyncio.CancelledError,BrokenPipeError):return
    async def consume(self):
        try:
            while self.running:
                raw=await self.processes[-1].stdout.readline()
                if not raw:break
                try:data=json.loads(raw)
                except Exception:
                    self.counters['invalid_outputs']+=1
                    continue
                await self.broadcast(data)
        except asyncio.CancelledError:return
    async def read_stderr(self,name,proc):
        try:
            while self.running:
                raw=await proc.stderr.readline()
                if not raw:break
                await self.broadcast({'type':'diagnostic','module':name,'message':raw.decode(errors='replace')[-400:]})
        except asyncio.CancelledError:return
    async def stop(self):
        self.running=False
        for task in self.tasks:task.cancel()
        for p in self.processes:
            if p.returncode is None:p.terminate()
        if self.processes:await asyncio.gather(*(p.wait() for p in self.processes),return_exceptions=True)
        self.tasks=[];self.processes=[]

hub=Hub()

@app.get('/health')
async def health():return JSONResponse({'status':'DEMO','source':'SYNTHETIC','streaming':hub.running,'frames':hub.counters['frames'],'service':'local-only'})

@app.websocket('/ws/telemetry')
async def telemetry(ws:WebSocket):
    origin=ws.headers.get('origin','')
    if origin not in ('http://localhost:5173','http://127.0.0.1:5173'):
        await ws.close(code=1008,reason='ORIGIN_DENIED');return
    required_token=os.environ.get('THREE_LABS_WS_TOKEN')
    if required_token and ws.query_params.get('token')!=required_token:
        await ws.close(code=1008,reason='TOKEN_DENIED');return
    await ws.accept();hub.clients.add(ws)
    try:
        await hub.start()
        await ws.send_json({'type':'hello','schema_version':'1.0','source':'SYNTHETIC','purpose':'RESEARCH_DEMO_ONLY'})
        while True:
            body=await ws.receive_json()
            if body.get('type')!='control' or set(body)-{'type','q_ca','gate_chi2'}:
                await ws.send_json({'type':'error','error':'CONTROL_SCHEMA_INVALID'});continue
            q=body.get('q_ca');g=body.get('gate_chi2')
            if ((q is not None and (type(q) not in (float,int) or not .001<=q<=50)) or
                (g is not None and (type(g) not in (float,int) or not 2<=g<=30))):
                await ws.send_json({'type':'error','error':'CONTROL_VALUE_OUT_OF_RANGE'});continue
            await hub.write(body)
    except WebSocketDisconnect:pass
    finally:
        hub.clients.discard(ws)
        if not hub.clients:await hub.stop()

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8787,ws_max_size=4096)
