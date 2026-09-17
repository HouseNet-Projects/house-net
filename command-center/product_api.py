"""Small production operator API over the canonical Deputy runtime.

It is intentionally a thin controller: all intelligence, state and mutation
rules remain in Deputy, Store and Action Runtime.  Bind to localhost by
default; set ``DEPUTY_OPERATOR_TOKEN`` for authenticated non-local hosting.
"""
from __future__ import annotations
import json, os, pathlib, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sys
ROOT=pathlib.Path(__file__).resolve().parent
for p in (ROOT/".claude"/"architecture", ROOT/".claude"/"skills", ROOT/".claude"/"integrations"):
    sys.path.insert(0,str(p))
import deputy, company_cockpit, proactive, execution_surface

def _token(): return os.environ.get("DEPUTY_OPERATOR_TOKEN")
def _auth(h):
    required=_token()
    if not required: return h.client_address[0] in ("127.0.0.1","::1")
    return h.headers.get("Authorization","") == "Bearer " + required

class Handler(BaseHTTPRequestHandler):
    server_version="HouseNetDeputy/1.0"
    def _json(self, code, body):
        raw=json.dumps(body,ensure_ascii=False,default=str).encode(); self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=="/health": return self._json(200,{"status":"alive"})
        if not _auth(self): return self._json(401,{"status":"UNAUTHORIZED"})
        if path in ("/cockpit","/reports/daily"): return self._json(200,company_cockpit.query("Give me today's company cockpit"))
        if path=="/attention": return self._json(200,company_cockpit.query("What needs my attention?").get("waiting_approvals",[]))
        if path=="/approvals": return self._json(200,execution_surface.approval_inbox())
        if path=="/sources": return self._json(200,company_cockpit.build_snapshot()["source_health"])
        if path=="/notifications": return self._json(200,proactive.events())
        if path=="/capabilities": return self._json(200,execution_surface.capability_matrix())
        if path=="/missions": return self._json(200,deputy.engine._store().list("commitments", limit=200))
        if path=="/history": return self._json(200,deputy.engine._store().list("audit", limit=200))
        if path=="/search":
            q=(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("q") or [""])[0].casefold()
            rows=[]
            for table in ("commitments","loops","actions","audit","tickets"):
                for row in deputy.engine._store().list(table, limit=200):
                    if q and q in json.dumps(row, ensure_ascii=False, default=str).casefold(): rows.append({"table":table,"record":row})
            return self._json(200,rows[:200])
        if path=="/readiness": return self._json(200,{"status":"ready","optional_sources":"degraded states are explicit"})
        return self._json(404,{"status":"NOT_FOUND"})
    def do_POST(self):
        if not _auth(self): return self._json(401,{"status":"UNAUTHORIZED"})
        path=urllib.parse.urlparse(self.path).path
        try: body=json.loads(self.rfile.read(min(int(self.headers.get("Content-Length",0)),65536)))
        except Exception: return self._json(400,{"status":"INVALID_JSON"})
        if path=="/ask":
            q=str(body.get("intent") or "").strip()
            if not q: return self._json(400,{"status":"BLOCKED","reason":"intent required"})
            return self._json(200,deputy.run(q,as_json=True))
        if path=="/preview": return self._json(200,execution_surface.preview(body.get("actions") or []))
        return self._json(404,{"status":"NOT_FOUND"})
    def log_message(self,*args): return

def serve(host="127.0.0.1",port=8765):
    server=ThreadingHTTPServer((host,port),Handler); server.serve_forever()

if __name__=="__main__": serve(os.environ.get("DEPUTY_BIND","127.0.0.1"),int(os.environ.get("DEPUTY_PORT","8765")))
