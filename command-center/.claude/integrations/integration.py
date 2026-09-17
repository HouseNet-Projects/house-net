# -*- coding: utf-8 -*-
"""Deputy integration CLI (read-only).
  python .claude/integrations/integration.py status                       one line per integration: health · certification · last read · unblock
  python .claude/integrations/integration.py query <id> <op> ['{json}']   normalized envelope (records truncated in the print)
  python .claude/integrations/integration.py probe                        Outlook reader probe (accounts, calendars, counts)
  python .claude/integrations/integration.py brief [YYYY-MM-DD]           live context for the Daily Brief (calendar + mail + health)
  python .claude/integrations/integration.py capability "<intent>"        structured write-intent verdict
  python .claude/integrations/integration.py certify [--no-real]          evidence-based certification (writes certification.json)
  python .claude/integrations/integration.py readiness                    activation view: implementation · configuration (missing field NAMES) · identity · read/write certification · deferral"""
import sys, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")

def _j(o): return json.dumps(o, ensure_ascii=False, indent=1, default=str)

def main(argv):
    cmd = argv[0] if argv else "status"
    import layer
    if cmd == "status":
        for s in layer.status():
            print(f"{s['integration_id']:12} {s['certification']:14} health={s['health']:16} last_success={s['last_success'] or '—':19} configured={s['configured']!s:5} ops={s['read_ops']} write_ops=[]")
            if s["unblock"] and s["certification"] in ("DECLARED", "CONFIGURED"): print(f"{'':12} ↳ unblock: {s['unblock'][:160]}")
        return 0
    if cmd == "query" and len(argv) >= 3:
        params = json.loads(argv[3]) if len(argv) > 3 else {}
        env = layer.query(argv[1], argv[2], params, use_cache="--no-cache" not in argv)
        view = dict(env); view["records"] = env.get("records", [])[:10]; view["stale_records"] = (env.get("stale_records") or [])[:3]
        print(_j(view)); return 0 if env["status"] == "OK" else 1
    if cmd == "probe":
        import adapter_outlook
        try: print(_j(adapter_outlook.probe())); return 0
        except Exception as e: print(f"probe FAILED: {e}"); return 1
    if cmd == "brief":
        ctx = layer.brief_context(argv[1] if len(argv) > 1 else None)
        print("\n".join(ctx["health_lines"])); print(f"meetings: {ctx['calendar']['count']} · mail: {ctx['mail']['count']} · unavailable: {ctx['unavailable']} · mode {ctx['mode']}")
        for r in ctx["calendar"].get("records", [])[:10]: print(f"  {r['start']} {r['title'][:50]} ({r['participant_count']} participants)")
        return 0
    if cmd == "capability" and len(argv) > 1:
        print(_j(layer.capability(argv[1]))); return 0
    if cmd == "certify":
        import certify_integrations; return certify_integrations.main(argv[1:])
    if cmd == "readiness":
        import readiness; print(readiness.render()); return 0
    print(__doc__); return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
