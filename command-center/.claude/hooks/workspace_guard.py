# -*- coding: utf-8 -*-
"""WORKSPACE GUARD — Claude Code hook (PreToolUse · PostToolUse) enforcing .claude/policy/workspace_policy.json.

Source of truth: validate_workspace.check_path / validate_tree (imported — no duplicate rule set here).
  PreToolUse   Write/Edit/MultiEdit/NotebookEdit → the target path is checked BEFORE the file exists; violations are DENIED.
               Bash/PowerShell → move/copy/create/redirect targets are parsed out of the command and checked BEFORE execution;
               deleting a required canonical file is DENIED. Targets that cannot be parsed are not "allowed" silently:
               PostToolUse validates the whole tree right after the command and FAILS LOUDLY (it cannot block post-hoc).
  PostToolUse  after any mutating tool: full-tree validation; violations are reported as a systemMessage + context for the model.
Fail-closed: a corrupt/missing policy denies every mutating tool. WORKSPACE_ROOT / WORKSPACE_POLICY env override for tests."""
import sys, json, os, re, pathlib
ROOT = pathlib.Path(os.environ.get("WORKSPACE_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
POLICY_DIR = pathlib.Path(__file__).resolve().parent.parent / "policy"
sys.path.insert(0, str(POLICY_DIR.parent / "runtime")); import python_runtime; python_runtime.ensure(auto_bootstrap=False)   # project interpreter only (hook.sh bootstraps)
sys.path.insert(0, str(POLICY_DIR))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

STATE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Monitor"}
MOVE_VERBS = re.compile(r"\b(mv|cp|mkdir|touch|rename|Move-Item|Copy-Item|New-Item|Rename-Item|ren|move|copy|md)\b", re.I)
DELETE_VERBS = re.compile(r"\b(rm|del|Remove-Item|unlink|rmdir)\b", re.I)
PATH_TOKEN = re.compile(r"\"([^\"]+)\"|'([^']+)'|(\S+)")

def out(obj=None, code=0):
    if obj is not None: print(json.dumps(obj, ensure_ascii=False))
    sys.exit(code)

def deny(reason):
    out({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}})

def load():
    import validate_workspace as vw
    pol = vw.load_policy(os.environ.get("WORKSPACE_POLICY") or (POLICY_DIR / "workspace_policy.json"))
    return vw, pol

def _inside(p):
    try: pathlib.Path(p).resolve().relative_to(ROOT.resolve()); return True
    except ValueError: return False

def _tokens(s):
    return [a or b or c for a, b, c in PATH_TOKEN.findall(s)]

def bash_targets(cmd):
    """Best-effort extraction of filesystem targets a shell command will CREATE/MOVE/COPY inside the workspace.
    Returns [(path, is_dir)]. Unparseable commands yield [] — PostToolUse then validates the real tree."""
    targets = []
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\n.*?\n\1\s*$", " ", cmd, flags=re.S | re.M)      # heredoc bodies are data, not shell
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\n.*", " ", cmd, flags=re.S)                     # unterminated heredoc → drop the rest
    for seg in re.split(r"\s*(?:&&|\|\||;|\|)\s*", cmd):
        toks = _tokens(seg)
        if not toks: continue
        verb = os.path.basename(toks[0]).lower()
        args = [t for t in toks[1:] if not t.startswith("-")]
        if verb in ("mv", "cp", "move", "copy", "rename", "ren", "move-item", "copy-item", "rename-item") and len(args) >= 2:
            dest = args[-1]; srcs = args[:-1]
            is_dir = any(os.path.isdir(s) for s in srcs) or dest.endswith(("/", "\\"))
            targets.append((dest, is_dir))
        elif verb in ("mkdir", "md") and args:
            targets += [(a, True) for a in args]
        elif verb == "touch" and args:
            targets += [(a, False) for a in args]
        elif verb == "new-item":
            m = re.search(r"-Path\s+(\"[^\"]+\"|'[^']+'|\S+)", seg) or re.search(r"New-Item\s+(\"[^\"]+\"|'[^']+'|\S+)", seg, re.I)
            if m: targets.append((m.group(1).strip("\"'"), "Directory" in seg))
        for m in re.finditer(r"(?:^|(?<=\s)|(?<=\d))>{1,2}\s*(\"[^\"]+\"|'[^']+'|\S+)", seg):        # shell redirect: ` > f`, `2>f`, `>>f`
            t = m.group(1).strip("\"'")
            if t.startswith("&") or t.lower() in ("/dev/null", "nul", "$null") or t.startswith("$"): continue     # fd redirects, null sinks, shell vars
            targets.append((t, False))
    return [(t, d) for t, d in targets if not t.startswith("-") and not t.startswith("&")]

def bash_deletes(cmd):
    dels = []
    for seg in re.split(r"\s*(?:&&|\|\||;|\|)\s*", cmd):
        toks = _tokens(seg)
        if toks and DELETE_VERBS.match(os.path.basename(toks[0])): dels += [t for t in toks[1:] if not t.startswith("-")]
    return dels

def on_pretool(data, vw, pol):
    tool, inp = data.get("tool_name", ""), data.get("tool_input") or {}
    if tool not in STATE_TOOLS: out(None, 0)
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = inp.get("file_path") or inp.get("notebook_path") or ""
        if p and _inside(p):
            probs = vw.check_path(p, pol, ROOT, is_dir=False)
            if probs: deny("WORKSPACE POLICY: " + " | ".join(probs) + "  → choose a compliant location/name (see .claude/policy/workspace_policy.json).")
        out(None, 0)
    cmd = str(inp.get("command", ""))
    required = set(pol["root"]["required_files"]) | {c for c, sp in pol["canonical_files"].items() if sp.get("single_canonical")} | {f"{a}/{f}" for a, d in pol["directories"].items() for f in d.get("required_files", [])}
    for d in bash_deletes(cmd):
        if _inside(d):
            try: rel = pathlib.Path(d).resolve().relative_to(ROOT.resolve()).as_posix()
            except ValueError: continue
            if rel in required: deny(f"WORKSPACE POLICY: {rel} is a required canonical file; deleting it is forbidden.")
    problems = []
    for target, is_dir in bash_targets(cmd):
        if not _inside(target): continue
        problems += vw.check_path(target, pol, ROOT, is_dir=is_dir)
    if problems: deny("WORKSPACE POLICY (pre-execution): " + " | ".join(sorted(set(problems))))
    out(None, 0)

def on_posttool(data, vw, pol):
    tool = data.get("tool_name", "")
    if tool not in STATE_TOOLS: out(None, 0)
    probs = vw.validate_tree(ROOT, pol)
    if probs:
        msg = f"⚠ WORKSPACE VIOLATION after {tool}: {len(probs)} problem(s) — " + " | ".join(probs[:6]) + (" …" if len(probs) > 6 else "")
        out({"hookSpecificOutput": {"hookEventName": "PostToolUse", "systemMessage": msg,
                                    "additionalContext": "WORKSPACE VIOLATION — the tree no longer satisfies .claude/policy/workspace_policy.json. Fix before finishing:\n  - " + "\n  - ".join(probs[:20])}})
    out(None, 0)

def main():
    raw = sys.stdin.read()
    try: data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError: data = {}
    ev = data.get("hook_event_name") or (sys.argv[1] if len(sys.argv) > 1 else "")
    try: vw, pol = load()
    except Exception as e:
        if ev == "PreToolUse" and data.get("tool_name") in STATE_TOOLS: deny(f"WORKSPACE POLICY unavailable ({type(e).__name__}: {e}) — fail closed; repair .claude/policy first.")
        print(f"⚠ workspace policy unavailable: {type(e).__name__}: {e}"); out(None, 0)
    if ev == "PreToolUse": on_pretool(data, vw, pol)
    elif ev == "PostToolUse": on_posttool(data, vw, pol)
    out(None, 0)

if __name__ == "__main__":
    main()
