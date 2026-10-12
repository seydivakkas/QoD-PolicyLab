import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Activity,Radio,Thermometer,Network,SlidersHorizontal,ShieldAlert,Layers3,ScanLine,Clock3,GitBranch,Wifi,Info,CircleDot,ChartNoAxesCombined} from 'lucide-react';
import './styles.css';

type Matrix=[[number,number],[number,number]];
type Projection={status:string;x_m?:number;y_m?:number;covariance_m2?:Matrix;ellipse95?:{major_m:number;minor_m:number;angle_deg:number};};
type Track={track_id:number;projection:Projection;velocity_mps?:number[]|null;speed_kmh?:number|null;valid:boolean;status:string;ttc?:{ttc_s:number|null;ttc_lower_s:number|null;sigma_s:number|null;status:string}|null;action?:string};
type Telemetry={type:string;timestamp_s:number;tracks:Track[];ttc_lower_s:number|null;action:string;service_cost_units:number;request_count:number;session_state:string;latency_margin_ms:number|null;source:string;};
const fmt=(n:number|null|undefined,suffix='')=>n==null||!Number.isFinite(n)?'—':n.toFixed(2)+suffix;

function RoadCanvas({data}:{data:Telemetry|null}){
 const canvas=useRef<HTMLCanvasElement>(null);const state=useRef<Telemetry|null>(null);state.current=data;
 useEffect(()=>{
  let id=0;const el=canvas.current!;const ctx=el.getContext('2d')!;
  const render=()=>{
   const rect=el.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1),w=rect.width,h=rect.height;
   if(el.width!==Math.round(w*dpr)||el.height!==Math.round(h*dpr)){el.width=Math.round(w*dpr);el.height=Math.round(h*dpr)}
   ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
   ctx.fillStyle='#101a24';ctx.fillRect(0,0,w,h);
   // view maps world X downstream, world Y lateral. All geometry is display-only.
   const world=(x:number,y:number):[number,number]=>[w*.12+x*(w*.76/42),h*.5+y*(h*.12)];
   const a=world(0,-6),b=world(42,6);ctx.fillStyle='#1a2935';ctx.fillRect(a[0],a[1],b[0]-a[0],b[1]-a[1]);
   ctx.strokeStyle='#334455';ctx.lineWidth=1;
   for(let x=0;x<=42;x+=6){const f=world(x,-11),t=world(x,11);ctx.beginPath();ctx.moveTo(...f);ctx.lineTo(...t);ctx.stroke()}
   for(let y=-6;y<=6;y+=3){ctx.setLineDash(y===0?[12,12]:[]);ctx.strokeStyle=y===0?'#82909d':'#354858';ctx.lineWidth=y===0?1.5:1;const f=world(0,y),t=world(42,y);ctx.beginPath();ctx.moveTo(...f);ctx.lineTo(...t);ctx.stroke()}
   ctx.setLineDash([]);
   const haz=world(32,0);ctx.strokeStyle='#ffbd72';ctx.beginPath();ctx.moveTo(haz[0],a[1]);ctx.lineTo(haz[0],b[1]);ctx.stroke();ctx.font='12px ui-sans-serif';ctx.fillStyle='#ffbd72';ctx.fillText('Kritik çizgi (sentetik)',haz[0]+8,b[1]-12);
   for(const track of state.current?.tracks||[]){
    const p=track.projection;if(p.x_m==null||p.y_m==null)continue;
    const [x,y]=world(p.x_m,p.y_m);if(x<0||x>w||y<0||y>h)continue;
    const good=track.valid&&p.status==='VALID';const color=good?'#58e8cb':'#f7ac76';
    if(p.covariance_m2&&p.ellipse95){const cov=p.covariance_m2;
     const cx=w*.76/42,cy=h*.12;const A=cov[0][0]*cx*cx,B=cov[0][1]*cx*cy,C=cov[1][1]*cy*cy;
     const delta=Math.sqrt(Math.max(0,(A-C)**2+4*B*B));const m=Math.max(0,(A+C+delta)/2),n=Math.max(0,(A+C-delta)/2);
     const angle=.5*Math.atan2(2*B,A-C);
     ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.beginPath();ctx.ellipse(0,0,Math.min(220,Math.sqrt(5.991*m)),Math.min(220,Math.sqrt(5.991*n)),0,0,Math.PI*2);ctx.fillStyle=good?'rgba(88,232,203,.09)':'rgba(247,172,118,.08)';ctx.strokeStyle=good?'rgba(88,232,203,.58)':'rgba(247,172,118,.6)';ctx.fill();ctx.stroke();ctx.restore();}
    if(track.velocity_mps){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+track.velocity_mps[0]*14,y+track.velocity_mps[1]*11);ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.stroke()}
    ctx.save();ctx.translate(x,y);ctx.fillStyle=color;ctx.shadowColor=color;ctx.shadowBlur=12;ctx.fillRect(-8,-4,16,8);ctx.restore();ctx.font='12px ui-sans-serif';ctx.fillStyle='#edf4fb';ctx.fillText('ID '+track.track_id,x+12,y-7);
   }
   id=requestAnimationFrame(render);
  };render();return()=>cancelAnimationFrame(id);
 },[]);
 return <canvas ref={canvas} className="road-canvas" role="img" aria-label="Sentetik yol, izlenen nesneler ve yüzde 95 metrik konum hata elipsleri"/>;
}

function Stat({label,value,note}:{label:string;value:string;note:string}){return <div className="stat"><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-foot">{note}</div></div>}
function Trend({values}:{values:number[]}){const w=288,h=66;if(values.length<2)return <div className="empty-chart">Akış verisi bekleniyor</div>;const ymin=Math.min(...values),ymax=Math.max(...values);const d=Math.max(.05,ymax-ymin);return <svg viewBox={`0 0 ${w} ${h}`} className="trend" role="img" aria-label="Geçmiş TTC alt sınırı çizgisi"><defs><linearGradient id="fade" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#58e8cb" stopOpacity=".22"/><stop offset="100%" stopColor="#58e8cb" stopOpacity="0"/></linearGradient></defs><path d={'M'+values.map((v,i)=>`${i*w/(values.length-1)},${h-7-(v-ymin)/d*(h-15)}`).join('L')} fill="none" stroke="#58e8cb" strokeWidth="2"/><path d={'M0,'+h+' L'+values.map((v,i)=>`${i*w/(values.length-1)},${h-7-(v-ymin)/d*(h-15)}`).join('L')+` L${w},${h} Z`} fill="url(#fade)"/></svg>}
function App(){
 const [online,setOnline]=useState(false),[event,setEvent]=useState<Telemetry|null>(null),[log,setLog]=useState<string[]>([]),[history,setHistory]=useState<number[]>([]),[q,setQ]=useState(.6),[gate,setGate]=useState(9.21),[tab,setTab]=useState<'overview'|'kalman'|'bev'|'qod'>('overview');
 const ws=useRef<WebSocket|null>(null);
 useEffect(()=>{
  let alive=true;let socket:WebSocket;
  const connect=()=>{if(!alive)return;socket=new WebSocket('ws://127.0.0.1:8787/ws/telemetry');ws.current=socket;
   socket.onopen=()=>{setOnline(true);setLog(s=>['Yerel simülasyon bağlantısı açıldı',...s].slice(0,7))};
   socket.onclose=()=>{setOnline(false);if(alive)setTimeout(connect,2500)};
   socket.onmessage=e=>{let d:any;try{d=JSON.parse(e.data)}catch{return};
    if(d.type==='telemetry'){setEvent(d);if(d.ttc_lower_s!=null)setHistory(v=>[...v,d.ttc_lower_s].slice(-60));if(d.action==='LOCAL_FAILSAFE_REQUIRED')setLog(v=>[`t=${d.timestamp_s.toFixed(1)}: yerel failsafe UYARISI (simülasyon)`,...v].slice(0,7))}
    else if(d.type==='control_ack')setLog(v=>[`Kontrol uygulandı: q_ca=${d.q_ca}, gate=${d.gate_chi2}`,...v].slice(0,7));
    else if(d.type==='error'||d.type==='diagnostic')setLog(v=>[String(d.detail||d.message||d.error||'unknown').slice(0,100),...v].slice(0,7));
   }};connect();return()=>{alive=false;socket?.close()};},[]);
 const submit=(field:'q_ca'|'gate_chi2',n:number)=>{if(ws.current?.readyState===WebSocket.OPEN)ws.current.send(JSON.stringify({type:'control',[field]:n}))};
 const labels={overview:'Genel Bakış',kalman:'KalmanTrackLab',bev:'BEV-MotionLab',qod:'QoD-PolicyLab'};
 return <div className="shell">
 <aside className="sidebar"><div className="brand"><div className="brand-icon"><Layers3 size={22}/></div><div><strong>THREE<span>LABS</span></strong><small>LOCAL RESEARCH SUITE</small></div></div>
 <div className="nav-title">ÇALIŞMA ALANI</div><nav>{([['overview',Activity],['kalman',ScanLine],['bev',Layers3],['qod',Network]] as const).map(([id,Icon])=><button key={id} className={'nav-item '+(tab===id?'selected':'')} onClick={()=>setTab(id)}><Icon size={17}/>{labels[id]}</button>)}</nav>
 <div className="sidebar-bottom"><div className="online-indicator"><span className={'dot '+(online?'on':'')}/>{online?'Yerel servis bağlı':'Servis bekleniyor'}</div><span>CPU-first · Offline · v0.1 prototype</span></div></aside>
 <main className="main"><header className="topbar"><div><span className="overline">ENGINEERING / LIVE SIMULATION</span><h1>{labels[tab]}</h1><p>Üç bağımsız backend, tek gözlemlenebilir sentetik veri hattı</p></div><div className="top-pills"><span className="pill orange"><CircleDot size={13}/> BACKEND HOLD</span><span className="pill"><Radio size={14}/> SYNTHETIC</span></div></header>
 <section className="stats"><Stat label="AKTİF NESNELER" value={String(event?.tracks.filter(t=>t.valid).length||0)} note="Geçerli BEV hız izleri"/><Stat label="TTC ALT SINIRI" value={fmt(event?.ttc_lower_s,' s')} note="%95 tek yönlü yaklaşık"/><Stat label="AĞ GECİKME MARJI" value={fmt(event?.latency_margin_ms,' ms')} note="Sentetik p99=300 ms"/><Stat label="QOD HARCAMASI" value={fmt(event?.service_cost_units,' birim')} note="Model ücret birimi"/></section>
 <div className="content-grid"><section className="viewer panel"><div className="panel-header"><div><h2>Bird's Eye View <span>/ Live Tracks</span></h2><p>Kalman → Jacobian / BEV → TTC / QoD</p></div><span className="micro">SIM · XY METRE</span></div><div className="viewer-stage"><RoadCanvas data={event}/><span className="viewer-note"><span className="dot on"/> Live synthetic scene · 2D world projection</span></div><div className="viewer-footer"><span><span className="legend-dot teal"/> Onaylı metrik durum</span><span><span className="legend-dot amber"/> Belirsiz / durdurulmuş</span><span>Kesikli çizgi: referans şerit</span></div></section>
 <aside className="metrics panel"><div className="panel-header"><div><h2>Telemetry Metrics</h2><p>Güncel karar ve performans</p></div><Activity size={19} color="#58e8cb"/></div><div className="metric-block"><span className="overline">TTC · SON 60 ÖRNEK</span><Trend values={history}/></div><div className="metrics-list"><div><span>QoD Oturumu</span><strong>{event?.session_state||'—'}</strong></div><div><span>Karar</span><strong className={event?.action==='LOCAL_FAILSAFE_REQUIRED'?'warn':''}>{event?.action||'—'}</strong></div><div><span>İstek adedi</span><strong>{event?.request_count??0}</strong></div><div><span>Kaynak</span><strong>Sentetik / CPU</strong></div></div><div className="warning-box"><ShieldAlert size={17}/><div>Gerçek çarpışma olasılığı veya 5G SLA değildir. Failsafe göstergesi fiziksel fren komutu göndermez.</div></div></aside>
 <section className="panel control-panel"><div className="panel-header"><div><h2><SlidersHorizontal size={17}/> Motion Model Controls</h2><p>Çift yönlü WebSocket kontrolü</p></div><span className="micro">EXPERIMENTAL</span></div><div className="slider"><div><span>IMM · CA jerk standard sapması</span><strong>{q.toFixed(2)}</strong></div><input aria-label="CA jerk standart sapması" type="range" min="0.1" max="5" step="0.05" value={q} onChange={e=>{let n=+e.target.value;setQ(n);submit('q_ca',n)}}/><small>Sistem varsayılanlarını etkiler; kabul koşullarını değiştirmez.</small></div><div className="slider"><div><span>Mahalanobis eşik değeri (χ²)</span><strong>{gate.toFixed(2)}</strong></div><input aria-label="Mahalanobis eşik değeri" type="range" min="2" max="20" step="0.1" value={gate} onChange={e=>{let n=+e.target.value;setGate(n);submit('gate_chi2',n)}}/><small>Yalnız mevcut simülasyon izlemesinde etkindir.</small></div></section>
 <section className="panel logs"><div className="panel-header"><div><h2><Clock3 size={17}/> Olay Günlüğü</h2><p>FSM / uyarılar / runtime kontroller</p></div><span className="micro">LAST 7</span></div>{log.length?log.map((v,i)=><div key={i} className="log-line"><span>{String(i+1).padStart(2,'0')}</span>{v}</div>):<div className="empty-chart">Henüz olay kaydı bulunmuyor</div>}</section></div>
 <footer><Info size={13}/> Scientific prototype · Gerçek video ve operatör verisi çalıştırılmadı · HOTA/IDF1 ve fiziksel hız kabulü HOLD · Canvas görüntülemesi GPU/60 FPS garantisi değildir</footer>
 </main></div>
}
createRoot(document.getElementById('root')!).render(<App/>);
