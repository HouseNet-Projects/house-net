# -*- coding: utf-8 -*-
"""Deputy Daily Brief — SessionStart hook. Routed THROUGH the certified Skill Engine on a governed gate ticket:
daily_briefing + commitment_memory run via engine.run_skill → audited, verified. Also validates the workspace contract
and reports enforcement health (escaped tickets, stale certifications, store integrity). Falls back to a direct
Tasks.xlsx read only if the engine is unavailable — and says so."""
import os, sys, io, datetime, pathlib, json
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent          # Command-center/ (workspace root)
sys.path.insert(0, str(ROOT / ".claude" / "runtime")); import python_runtime; python_runtime.ensure(auto_bootstrap=False)   # project interpreter only (hook.sh bootstraps)
sys.path.insert(0, str(ROOT / ".claude" / "skills")); sys.path.insert(0, str(ROOT / ".claude" / "policy"))
TODAY = datetime.date.today()
HY = ["երկուշաբթի","երեքշաբթի","չորեքշաբթի","հինգշաբթի","ուրբաթ","շաբաթ","կիրակի"]
try:
    IDENT = json.loads((ROOT / ".claude" / "policy" / "workspace_policy.json").read_text(encoding="utf-8"))["identity"]
except Exception:
    IDENT = {"name": "UNKNOWN", "role": "UNKNOWN", "workspace": "UNKNOWN", "owner_native": "Գև"}

def line(): print("─" * 56)
def d(x): return x[5:] if isinstance(x, str) and len(x) >= 10 else (x or "—")

print(); line()
print(f"  ⛔ {IDENT['name']} DAILY BRIEF — {TODAY.isoformat()}, {HY[TODAY.weekday()]}  ·  {IDENT['workspace']}")
print(f"  Դու {IDENT['name']}-ն ես՝ {IDENT['owner_native']}-ի {IDENT['role']}։ Գործիր ըստ CLAUDE.md-ի։ Skill gate՝ մեխանիկական (hooks)։")
line()

# 0) workspace contract
try:
    import validate_workspace as vw
    probs = vw.validate_tree(ROOT)
    if probs:
        print(f"\n  🧱 WORKSPACE CONTRACT — {len(probs)} խախտում (ուղղիր ԱՌԱՋԻՆԸ)՝")
        for p in probs[:8]: print(f"       ✗ {p}")
        if len(probs) > 8: print(f"       … և {len(probs) - 8} ևս (python .claude/policy/validate_workspace.py)")
    else: print("\n  🧱 workspace contract ✓")
except Exception as e: print(f"\n  🧱 workspace validator unavailable ({type(e).__name__}: {e}) — fail closed: consider the tree UNVERIFIED")

# 0b) durability drift — is GitHub main current? (LIVE DATA SYNC vs PRODUCT RELEASE; never pretend the repo is synced)
try:
    sys.path.insert(0, str(ROOT / ".claude" / "runtime")); import data_sync
    dr = data_sync.plan(ROOT); ch = dr["changes"]; cd = dr["checksum_drift"]
    if dr["state"] == "CLEAN": print("  🔄 GitHub sync ✓ (clean, ahead 0)")
    else:
        detail = " · ".join(f"{k} {', '.join(pathlib.Path(p).name for p in v[:3])}{'…' if len(v) > 3 else ''}" for k, v in list(ch.items()) + [(f"checksum:{k}", v) for k, v in cd.items()])
        hint = {"SYNC_REQUIRED": "վազեցրու skill.py sync", "RELEASE_REQUIRED": "product/model փոփոխություն — skill.py release", "UNCLASSIFIED": "անհայտ ուղի — ոչինչ չի sync-վում, ստուգիր"}[dr["state"]]
        print(f"  🔄 GitHub ՉԻ ՀԱՄԱԺԱՄԱՆԱԿԵՑՎԱԾ — {dr['state']}" + (f" · ahead {dr['ahead']}" if dr.get("ahead") else "") + f" · {detail} → {hint}")
except Exception as e: print(f"  🔄 sync state unavailable ({type(e).__name__}: {e}) — consider GitHub NOT current")

# 1) inbox
import paths                                                            # ONE business-root resolver (sys.path already carries .claude/policy)
inbox = paths.biz("00_Inbox", repo_root=ROOT)
items = [f for f in os.listdir(inbox) if f != "Input.md"] if inbox.is_dir() else []
if items:
    print(f"\n  📥 {paths.to_repo('00_Inbox')} — {len(items)} ԱՆԴԱՍԱՎՈՐ ԲԱՆ, դասավորի ԱՌԱՋԻՆԸ՝")
    for f in items: print(f"       • {f}")
else: print(f"\n  📥 {paths.to_repo('00_Inbox')} դատարկ է ✓")

# 2) unprocessed text drop
try:
    raw = io.open(paths.inbox_input(ROOT), encoding="utf-8").read()
    seg = raw.split("## Չմշակված", 1); body = seg[1].split("---", 1)[0] if len(seg) > 1 else ""
    if "\n".join(l for l in body.splitlines() if l.strip() and not l.strip().startswith("<!--")).strip():
        print("\n  ✉  Input.md-ում կա չմշակված տեքստ — դարձրու առաջադրանք")
except Exception: pass

# 3) brief via the certified skill engine (audited, governed ticket)
engine_used = False
try:
    import engine
    reg = engine.load_registry()
    session = os.environ.get("CLAUDE_SESSION_ID", "")
    t = engine.open_ticket(reg, "session-start brief: daily_briefing + commitment_memory", session_id=session, source="SessionStart")
    r = engine.run_skill(reg, "daily_briefing", {}, intent="session-start brief", selection_reason="SessionStart hook", ticket_id=t["ticket_id"])
    if r["status"] == "BLOCKED" and any(b.get("code") == "STALE_SOURCE" for b in r.get("blocked", [])):
        print(f"\n  ⚠ ԱՂԲՅՈՒՐԸ ՀՆԱՑԱԾ Է — {r['blocked'][0]['reason']}\n     Բրիֆը տրվում է հնացած տվյալով (ընդունված, աուդիտված)։ Թարմացրու Tasks.xlsx-ը։")
        r = engine.run_skill(reg, "daily_briefing", {"accept_stale": True}, intent="session-start brief (stale acknowledged)", selection_reason="SessionStart hook", ticket_id=t["ticket_id"])
    if r["status"] == "EXECUTED":
        b = r["result"]; engine_used = True
        def show(title, rows, mark):
            if not rows: return
            print(f"\n  {mark} {title} — {len(rows)}")
            for x in rows: print(f"       {x['id']}. [{d(x.get('due'))}] {x['task'][:52]}  ·  {x.get('owner','')}")
        show("ԺԱՄԿԵՏԱՆՑ", b["overdue"], "🔴"); show("ԱՅՍՕՐ", b["deadlines_today"], "🟠"); show("ՎԱՂԸ", b["tomorrow"], "🟡")
        if b["waiting_for"]:
            print(f"\n  ⏳ ՍՊԱՍՈՒՄ ԵՄ ՈՒՐԻՇԻՑ — {len(b['waiting_for'])}")
            for w in b["waiting_for"]: print(f"       {w['id']}. {w['from']}  ·  {w['task'][:44]}  [{d(w.get('due'))}]")
        if b["decisions_pending"]:
            print(f"\n  ⚖  ՈՐՈՇՈՒՄ Է ՍՊԱՍՎՈՒՄ — {len(b['decisions_pending'])}")
            for x in b["decisions_pending"]: print(f"       {x['id']}. {x['task'][:52]}  ·  {x['owner']}")
        if b["no_deadline"]: print(f"\n  ⚠  Ժամկետ չունեցող բաց կետ՝ {len(b['no_deadline'])} — ժամկետ դիր")
        if not (b["overdue"] or b["deadlines_today"]): print("\n  ✓ Ժամկետանց կամ այսօրվա բաց կետ չկա")
        # LIVE (Mission 4, read-only): meetings · mail candidates · risks · preparation · integration health — nothing shown as current unless read now
        lvb = b.get("live") or {}
        for s in b.get("sections", []):
            items = [i for i in s["items"] if i.get("kind") in ("meeting", "email")] if s["id"] in ("TODAY", "OVERDUE", "WAITING_FOR", "DECISIONS") else s["items"]
            if not items: continue
            print(f"\n  ▶ {s['title']} ({s['id']}) — {len(items)}")
            for i in items[:8]: print(f"       {i['text'][:110]}")
            if s.get("note"): print(f"       ({s['note']})")
        for l in lvb.get("integration_health", []): print(f"  🔌 {l}")
        if lvb.get("available") is False: print(f"  🔌 live layer unavailable — {lvb.get('reason')}")
        for g in b.get("data_gaps", [])[:2]: print(f"  ∅ {g}")
        c = engine.run_skill(reg, "commitment_memory", {}, intent="session-start brief", selection_reason="SessionStart hook", ticket_id=t["ticket_id"])
        cm = c.get("result", {}).get("commitments", []) if c["status"] == "EXECUTED" else []
        due_soon = [x for x in cm if x.get("due") and x["due"] <= (TODAY + datetime.timedelta(days=3)).isoformat()]
        if due_soon:
            print(f"\n  📌 ԽՈՍՏՈՒՄՆԵՐ, ԺԱՄԿԵՏԸ ≤3 ՕՐ — {len(due_soon)}")
            for x in due_soon: print(f"       [{d(x['due'])}] {x['text'][:60]}")
        mg = b.get("management") or {}
        if mg.get("status") == "EXECUTED":
            tl = mg["TOP_LINE"]; print(f"\n  🎯 MANAGEMENT (Mission 5) · truth {mg.get('truth_mode')} · Gev-ին պետք է {tl['needs_gev']} · exceptions {tl['exceptions']} · {tl['highest'][:90]}")
            for q in mg.get("GEV_ACTION", [])[:4]: print(f"       ⚑ [{q['category']}] {q['issue'][:80]} → {q['required'][:60]}")
            for x in mg.get("ACTIONS", [])[:3]: print(f"       → {x[:120]}")
            ch = mg.get("CHANGES") or {}
            print("       Δ " + (("since " + str(ch.get('since'))[:16] + ": " + ", ".join(f"{k} {len(ch.get(k, []))}" for k in ("NEW", "CHANGED", "RESOLVED", "WORSENED", "NEEDS_GEV"))) if ch.get("available") else str(ch.get("reason", ""))[:90]))
        elif mg: print(f"\n  🎯 MANAGEMENT unavailable — {mg.get('reason')}")
        ver = r.get("verification", {}); dbs = reg["_index"]["daily_briefing"]
        print(f"\n  ⚙  skill engine: daily_briefing v{dbs['version']} ({dbs['maturity_level']}) · exec {r['execution_id']} · verified {'✓' if ver.get('ok') else '✗'} · ticket {t['ticket_id']}")
    else:
        print(f"\n  ⚠ daily_briefing skill {r['status']}: {r.get('blocked') or r.get('error')}")
    # enforcement health
    st = engine._store(); chk = st.check()
    cutoff = (datetime.datetime.now() - datetime.timedelta(hours=12)).isoformat(timespec="seconds")
    stale_open = [x for x in st.list("tickets", where="status='OPEN'") if x["ticket_id"] != t["ticket_id"] and x.get("created", "") < cutoff]
    for x in stale_open: engine.close_ticket(x["ticket_id"], "ABANDONED", "left open by a previous session")
    esc = [x for x in st.list("tickets") if (x.get("closure") or {}).get("verdict") == "ESCAPE"]
    probs_reg = engine.validate_registry(reg)
    flags = []
    if not chk["ok"]: flags.append(f"store integrity ✗ {chk['problems'][:1]}")
    if esc: flags.append(f"ENFORCEMENT ESCAPES ընդհանուր՝ {len(esc)} (վերջինը՝ {esc[-1]['ticket_id']}) — ստուգիր skill.py audit")
    if probs_reg: flags.append(f"certification problems՝ {len(probs_reg)} — վազեցրու skill.py release")
    if stale_open: flags.append(f"{len(stale_open)} բաց ticket փակվեց որպես ABANDONED")
    print("  🛡  enforcement: hooks gate(UserPromptSubmit/PreToolUse/PostToolUse/Stop) + workspace_guard · store " + ("ok" if chk["ok"] else "CORRUPT") + (" · " + " · ".join(flags) if flags else " · escapes 0 · certs fresh"))
    engine.close_ticket(t["ticket_id"], "GOVERNED_EXECUTED" if engine_used else "GOVERNED_BLOCKED_REPORTED", "session-start brief")
except Exception as e:
    print(f"\n  ⚠ skill engine unavailable ({type(e).__name__}: {e}) — fallback read, UNGOVERNED")

if not engine_used:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(paths.tasks(ROOT), data_only=True); ws = wb["ԱՌԱՋԱԴՐԱՆՔՆԵՐ"]
        over, today = [], []
        for r in range(13, ws.max_row + 1):
            n, task, st, due = ws.cell(row=r,column=2).value, ws.cell(row=r,column=3).value, ws.cell(row=r,column=6).value, ws.cell(row=r,column=11).value
            if not isinstance(n, int) or st == "Արված" or not hasattr(due, "date"): continue
            dd = due.date() if isinstance(due, datetime.datetime) else due
            (over if dd < TODAY else today if dd == TODAY else []).append(f"{n}. {task}")
        if over: print("\n  🔴 ԺԱՄԿԵՏԱՆՑ:", *[f"\n       {x}" for x in over])
        if today: print("\n  🟠 ԱՅՍՕՐ:", *[f"\n       {x}" for x in today])
    except Exception as e: print(f"\n  (Tasks.xlsx չկարդացվեց՝ {type(e).__name__})")

line(); print(f"  Հաղորդիր վերևը {IDENT['owner_native']}-ին ՆԱԽՔԱՆ մնացած գործը սկսելը։"); line(); print()
