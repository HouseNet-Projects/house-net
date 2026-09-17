"""Thin authenticated browser/API controller over canonical Deputy runtime."""
from __future__ import annotations
import json, os, pathlib, urllib.parse, sys, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ROOT=pathlib.Path(__file__).resolve().parent
for p in (ROOT/'.claude/architecture',ROOT/'.claude/skills',ROOT/'.claude/integrations'):
    sys.path.insert(0,str(p))
import deputy, company_cockpit, proactive, execution_surface, worker, actions

INDEX_HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HouseNet / Deputy</title><style>
:root{color-scheme:dark;--bg:#09131f;--panel:#102336;--panel2:#132c43;--line:#2d5068;--text:#e8f2f7;--muted:#91afc1;--brand:#8ed1ff;--good:#84e1b5;--warn:#ffd37a;--bad:#ff9b9b}*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,var(--bg),#0c1e31);color:var(--text);font:14px/1.5 system-ui,-apple-system,sans-serif}header{border-bottom:1px solid var(--line);padding:22px clamp(18px,4vw,52px);display:flex;justify-content:space-between;align-items:center;gap:20px}h1{font-size:24px;margin:0;color:var(--brand)}h2{margin:0 0 6px;font-size:20px}.eyebrow{color:var(--muted);text-transform:uppercase;letter-spacing:.12em;font-size:11px}.shell{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 84px)}nav{padding:20px 14px;border-right:1px solid var(--line)}nav button{display:block;width:100%;text-align:left;background:none;color:var(--text);border:0;border-radius:8px;padding:10px 12px;margin:3px 0;cursor:pointer}nav button:hover,nav button.active{background:var(--panel2);color:var(--brand)}main{padding:clamp(18px,4vw,48px);max-width:1300px;width:100%}.hero{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.card{background:rgba(16,35,54,.92);border:1px solid var(--line);border-radius:12px;padding:16px;min-height:90px}.card strong{display:block;color:var(--brand);font-size:20px}.card h3{margin:0 0 8px;font-size:15px}.list{display:grid;gap:10px;margin-top:18px}.item{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:13px}.item .meta{color:var(--muted);font-size:12px}.pill{display:inline-block;border:1px solid var(--line);border-radius:20px;padding:2px 8px;font-size:11px;margin-right:5px}.pill.good{color:var(--good)}.pill.warn{color:var(--warn)}.pill.bad{color:var(--bad)}button.primary{background:#1e5d80;border:1px solid #6eafd0;color:#fff;border-radius:7px;padding:8px 12px;cursor:pointer}input{background:#0b1a29;color:var(--text);border:1px solid var(--line);border-radius:7px;padding:9px}form{display:flex;gap:8px;flex-wrap:wrap}.empty,.error{color:var(--muted);padding:22px;text-align:center;border:1px dashed var(--line);border-radius:10px}pre{white-space:pre-wrap;overflow:auto;color:#c5dce8;font-size:12px}a{color:var(--brand)}@media(max-width:720px){.shell{display:block}nav{display:flex;overflow:auto;border-right:0;border-bottom:1px solid var(--line);gap:4px}nav button{white-space:nowrap;width:auto}.hero{display:block}}
</style></head><body><header><div><div class="eyebrow">HouseNet operating system</div><h1>Deputy</h1><div style="color:var(--muted)">Gev's governed operating surface</div></div><div id="health" class="pill">Checking service…</div></header><div class="shell"><nav aria-label="Primary"><button data-view="cockpit">Company Cockpit</button><button data-view="attention">Gev Attention</button><button data-view="approvals">Approval Inbox</button><button data-view="missions">Mission Center</button><button data-view="execution">Execution Center</button><button data-view="sources">Integration Health</button><button data-view="reports">Reports</button><button data-view="ask">Ask Deputy</button><button data-view="search">Search</button><button data-view="history">History / Timeline</button><button data-view="notifications">Notifications</button><button data-view="worker">Worker status</button></nav><main><div class="hero"><div><div class="eyebrow" id="eyebrow">Live company context</div><h2 id="title">Company Cockpit</h2></div><div id="updated" class="meta"></div></div><div id="content" aria-live="polite"></div></main></div><script src="/app.js"></script></body></html>'''
APP_JS = r'''// canonical ask route: fetch('/ask'
const content=document.querySelector('#content'),title=document.querySelector('#title'),eyebrow=document.querySelector('#eyebrow'),health=document.querySelector('#health'),updated=document.querySelector('#updated');let current='cockpit';const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const json=v=>typeof v==='object'?JSON.stringify(v,null,2):esc(v);function badge(v){let s=String(v??'UNKNOWN');let c=/VERIFIED|CURRENT|READY|GREEN|COMPLETED/.test(s)?'good':/STALE|WAIT|BLOCK|DEGRADED|REQUIRED|UNKNOWN/.test(s)?'warn':'bad';return `<span class="pill ${c}">${esc(s)}</span>`}function rows(data){if(!data||Array.isArray(data)&&!data.length)return '<div class="empty">No records currently available.</div>';if(Array.isArray(data))return `<div class="list">${data.map((x,i)=>`<article class="item"><div>${badge(x.state||x.status||x.level||'RECORD')} <strong>${esc(x.title||x.summary||x.action_id||x.event_type||x.source||x.mission||('Record '+(i+1)))}</strong></div><div class="meta">${esc(x.reason||x.effect||x.recommended_response||x.current_limitation||'')}</div>${x.action_id&&x.state==='APPROVAL_REQUIRED'?'<button class=\"primary\" data-approve=\"'+esc(x.action_id)+'\">Approve exact action</button> <button data-reject=\"'+esc(x.action_id)+'\">Reject</button>':''}<details><summary>Evidence</summary><pre>${esc(JSON.stringify(x,null,2))}</pre></details></article>`).join('')}</div>`;return rows([data])}function cards(d){let keys=Object.keys(d||{}).slice(0,8);return `<div class="grid">${keys.map(k=>`<div class="card"><div class="eyebrow">${esc(k.replaceAll('_',' '))}</div><strong>${typeof d[k]==='number'?d[k]:esc(Array.isArray(d[k])?d[k].length:d[k]?.status||d[k]||'—')}</strong></div>`).join('')}</div>`}async function api(path,opts){const r=await fetch(path,opts);const d=await r.json();if(!r.ok)throw new Error(d.reason||d.status||'Request failed');return d}async function load(view){current=view;document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));const map={cockpit:['/cockpit','Live company context'],attention:['/attention','Owner attention'],approvals:['/approvals','Exact Action Runtime decisions'],missions:['/missions','Durable missions and work graph'],execution:['/capabilities','Governed execution'],sources:['/sources','Source health and freshness'],reports:['/reports/daily','Derived reports'],notifications:['/notifications','Proactive events'],history:['/history','Sanitized audit timeline'],worker:['/worker','Operational status']};if(view==='ask'){return renderAsk()}if(view==='search'){return renderSearch()}let [path,sub]=map[view]||map.cockpit;title.textContent=({cockpit:'Company Cockpit',attention:'Gev Attention',approvals:'Approval Inbox',missions:'Mission Center',execution:'Execution Center',sources:'Integration Health',reports:'Reports',notifications:'Notifications',history:'History / Timeline',worker:'Worker status'})[view];eyebrow.textContent=sub;content.innerHTML='<div class="empty">Loading current state…</div>';try{const d=await api(path);updated.textContent='Updated '+new Date().toLocaleTimeString();content.innerHTML=cards(d)+rows(Array.isArray(d)?d:(d.items||d.events||d.actions||d.attention||d.source_health||d.waiting_approvals||[d]));if(view==='approvals')bindApprovals()}catch(e){content.innerHTML=`<div class="error">${esc(e.message)}<br><small>Core runtime remains authoritative; retry when the source is available.</small></div>`}}function bindApprovals(){document.querySelectorAll('[data-approve]').forEach(b=>b.onclick=async()=>{const id=b.dataset.approve;const text=prompt('Type an exact approval (for example: OK to approve this action)');if(text===null)return;try{await api('/approvals/'+encodeURIComponent(id)+'/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});load('approvals')}catch(e){alert(e.message)}});document.querySelectorAll('[data-reject]').forEach(b=>b.onclick=async()=>{const id=b.dataset.reject;try{await api('/approvals/'+encodeURIComponent(id)+'/reject',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:'Rejected by Gev'})});load('approvals')}catch(e){alert(e.message)}})}function renderAsk(){title.textContent='Ask Deputy';eyebrow.textContent='One canonical interaction path';content.innerHTML='<form id="ask"><input id="intent" aria-label="Deputy intent" size="54" placeholder="What is blocked in Sales?"><button class="primary">Ask Deputy</button></form><div id="answer" class="list"></div>';document.querySelector('#ask').onsubmit=async e=>{e.preventDefault();const q=document.querySelector('#intent').value.trim();if(!q)return;document.querySelector('#answer').innerHTML='<div class="empty">Deputy is assembling governed context…</div>';try{const d=await api('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({intent:q})});document.querySelector('#answer').innerHTML=rows([d])}catch(err){document.querySelector('#answer').innerHTML=`<div class="error">${esc(err.message)}</div>`}}}function renderSearch(){title.textContent='Search';eyebrow.textContent='Governed records only';content.innerHTML='<form id="search"><input id="query" aria-label="Search query" size="54"><button class="primary">Search</button></form><div id="results" class="list"></div>';document.querySelector('#search').onsubmit=async e=>{e.preventDefault();const q=document.querySelector('#query').value;document.querySelector('#results').innerHTML=rows(await api('/search?q='+encodeURIComponent(q)))}}document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>load(b.dataset.view));api('/health').then(d=>{health.textContent='Service '+(d.status||'alive');health.classList.add('good')}).catch(()=>{health.textContent='Service unavailable';health.classList.add('bad')});load('cockpit');'''

def _token(): return os.environ.get('DEPUTY_OPERATOR_TOKEN')
def _auth(h):
    required=_token()
    if not required: return h.client_address[0] in ('127.0.0.1','::1')
    return h.headers.get('Authorization','') == 'Bearer '+required

def _safe_action(a):
    if not a:return None
    x=dict(a); req=dict(x.get('request') or {}); req.pop('parameters',None); req.pop('source_context',None); req.pop('business_context',None); x['request']=req
    if x.get('approval'):
        x['approval']={k:v for k,v in x['approval'].items() if k not in ('approval_text',)}
    return x

class Handler(BaseHTTPRequestHandler):
    server_version='HouseNetDeputy/1.0'
    def _json(self,code,body):
        raw=json.dumps(body,ensure_ascii=False,default=str).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/health':return self._json(200,{'status':'alive'})
        if path=='/':return self._serve(INDEX_HTML,'text/html; charset=utf-8')
        if path=='/app.js':return self._serve(APP_JS,'application/javascript; charset=utf-8')
        if not _auth(self):return self._json(401,{'status':'UNAUTHORIZED'})
        try:
            if path in ('/cockpit','/reports/daily'):return self._json(200,company_cockpit.query("Give me today's company cockpit"))
            if path=='/attention':return self._json(200,company_cockpit.query('What needs my attention?'))
            if path=='/approvals':return self._json(200,execution_surface.approval_inbox())
            if path.startswith('/actions/'):
                return self._json(200,_safe_action(actions.get(path.split('/')[2])))
            if path=='/sources':return self._json(200,company_cockpit.build_snapshot()['source_health'])
            if path=='/notifications':return self._json(200,proactive.events())
            if path=='/worker':return self._json(200,worker.status())
            if path=='/capabilities':return self._json(200,execution_surface.capability_matrix())
            if path=='/missions':return self._json(200,deputy.engine._store().list('commitments',limit=200))
            if path=='/history':return self._json(200,deputy.engine._store().list('audit',limit=200))
            if path=='/search':
                q=(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('q') or [''])[0].casefold();out=[]
                for table in ('commitments','loops','actions','audit','tickets'):
                    for row in deputy.engine._store().list(table,limit=200):
                        if q and q in json.dumps(row,ensure_ascii=False,default=str).casefold():out.append({'table':table,'record':row})
                return self._json(200,out[:200])
            if path=='/readiness':return self._readiness()
            return self._json(404,{'status':'NOT_FOUND'})
        except Exception as e:return self._json(503,{'status':'DEGRADED','reason':type(e).__name__})
    def _serve(self,text,ctype):
        raw=text.encode();self.send_response(200);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(raw)));self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'unsafe-inline'; script-src 'self'");self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.end_headers();self.wfile.write(raw)
    def _readiness(self):
        checks={};errors=[]
        try: deputy.engine._store().list('commitments',limit=1);checks['store']='READY'
        except Exception as e:checks['store']='UNAVAILABLE';errors.append('store')
        try: checks['action_runtime']='READY' if callable(actions.execute) else 'UNAVAILABLE'
        except Exception:checks['action_runtime']='UNAVAILABLE';errors.append('action_runtime')
        checks['worker']=worker.status();checks['configuration']={'state_dir':str(deputy.engine._store().dir),'python':sys.executable}
        optional={}
        try:
            for iid,v in company_cockpit.build_snapshot().get('source_health',{}).items():optional[iid]=v.get('state') or v.get('level') or 'UNKNOWN'
        except Exception:optional={'state':'UNAVAILABLE'}
        core_ok=not errors;body={'status':'READY' if core_ok else 'DEGRADED','core':checks,'optional_sources':optional,'errors':errors}
        return self._json(200 if core_ok else 503,body)
    def do_POST(self):
        if not _auth(self):return self._json(401,{'status':'UNAUTHORIZED'})
        path=urllib.parse.urlparse(self.path).path
        try:
            n=int(self.headers.get('Content-Length','0')); 
            if n<0 or n>65536:return self._json(413,{'status':'REQUEST_TOO_LARGE'})
            body=json.loads(self.rfile.read(n) or b'{}')
        except Exception:return self._json(400,{'status':'INVALID_JSON'})
        try:
            if path=='/ask':
                q=str(body.get('intent') or '').strip()
                if not q:return self._json(400,{'status':'BLOCKED','reason':'intent required'})
                return self._json(200,deputy.run(q,as_json=True))
            if path=='/preview':return self._json(200,execution_surface.preview(body.get('actions') or []))
            parts=path.strip('/').split('/')
            if len(parts)==3 and parts[0]=='approvals':
                aid=urllib.parse.unquote(parts[1])
                if parts[2]=='approve':
                    out=actions.approve(str(body.get('text') or ''),action_id=aid)
                    return self._json(200 if out.get('status')=='APPROVED' else 409,out)
                if parts[2]=='reject':return self._json(200,actions.reject(aid,reason=str(body.get('reason') or 'Rejected by Gev')))
            if len(parts)==3 and parts[0]=='actions' and parts[2]=='execute':
                aid=urllib.parse.unquote(parts[1]);token=str(body.get('token_id') or '')
                if not token:return self._json(400,{'status':'APPROVAL_REQUIRED','reason':'exact token_id required'})
                return self._json(200,execution_surface.execute_approved(aid,token_id=token))
            return self._json(404,{'status':'NOT_FOUND'})
        except actions.ActionError as e:return self._json(409,{'status':e.code,'reason':e.reason})
        except Exception as e:return self._json(500,{'status':'FAILED','reason':type(e).__name__})
    def log_message(self,*args):return

def serve(host='127.0.0.1',port=8765):ThreadingHTTPServer((host,port),Handler).serve_forever()
if __name__=='__main__':serve(os.environ.get('DEPUTY_BIND','127.0.0.1'),int(os.environ.get('DEPUTY_PORT','8765')))
