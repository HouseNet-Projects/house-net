# -*- coding: utf-8 -*-
"""ADAPTER INT-OL-CAL / INT-OL-MAIL — Outlook desktop (MAPI) through the FIXED read-only PowerShell reader outlook_read.ps1.
Why a reader and not COM from Python: the running Outlook instance is reachable from PowerShell in this Windows session but
not from the Python process (CO_E_SERVER_EXEC_FAILURE); the reader is integrity-pinned (sha256 in registry.py) and contains no
write call, so the read-only boundary is structural: Python can only pass validated parameters to fixed operations.
Failure mapping: pwsh missing → TOOL_UNAVAILABLE · reader modified → READ_ONLY_VIOLATION · COM not reachable → UNAVAILABLE ·
access denied → PERMISSION_DENIED · non-JSON → MALFORMED_RESPONSE · missing keys → SCHEMA_CHANGED · other mailbox → WRONG_TENANT."""
import sys, pathlib, json, subprocess, shutil, hashlib, datetime, os, re
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from contracts import IntegrationError, ReadOnlyViolation
import normalize, registry

READER = HERE / "outlook_read.ps1"
OPS = {"INT-OL-CAL": ("calendar.events",), "INT-OL-MAIL": ("mail.list", "mail.search")}
FORBIDDEN_MEMBERS = re.compile(r"\.(Send|Save|SaveAs|Move|Delete|Copy|Forward|Reply|ReplyAll|Display|MarkAsTask|ClearTaskFlag|Add|Remove|CreateItem|CreateItemFromTemplate|Respond|PermanentlyDelete)\s*\(|\bSet-|\bRemove-Item|\.UnRead\s*=|\.Subject\s*=|\.Body\s*=", re.I)
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$")

def reader_sha256(): return hashlib.sha256(READER.read_bytes()).hexdigest() if READER.exists() else None

def reader_problems():
    """Static proof of the read-only boundary: the reader exists, matches its pin and contains no write member."""
    p = []
    if not READER.exists(): return ["outlook_read.ps1 missing"]
    if registry.OUTLOOK_READER_SHA256 == "PIN_PENDING": p.append("reader integrity pin not set (registry.OUTLOOK_READER_SHA256)")
    elif reader_sha256() != registry.OUTLOOK_READER_SHA256: p.append("outlook_read.ps1 does not match its integrity pin — modified reader refused")
    txt = READER.read_text(encoding="utf-8")
    for m in FORBIDDEN_MEMBERS.finditer(txt): p.append(f"forbidden write member in reader: {m.group(0).strip()}")
    return p

def pwsh():
    override = os.environ.get("COMMAND_CENTER_PWSH")
    if override: return override if pathlib.Path(override).exists() else None
    return shutil.which("pwsh") or shutil.which("powershell")

def _iso_or_raise(v, name):
    if not isinstance(v, str) or not _ISO.match(v): raise IntegrationError("BAD_PARAMS", f"{name} must be ISO date/time (got {v!r})")
    return v if "T" in v else v + "T00:00:00"

def _run(args, timeout=90):
    ps = pwsh()
    if not ps: raise IntegrationError("TOOL_UNAVAILABLE", "PowerShell (pwsh/powershell) not found — the Outlook reader cannot run")
    rp = reader_problems()
    if rp: raise ReadOnlyViolation("; ".join(rp))
    try:
        p = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(READER), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise IntegrationError("TIMEOUT", f"Outlook reader exceeded {timeout}s", retryable=True)
    except OSError as e:
        raise IntegrationError("TOOL_UNAVAILABLE", f"cannot start PowerShell: {e}")
    lines = [l for l in (p.stdout or "").splitlines() if l.strip()]
    if not lines: raise IntegrationError("MALFORMED_RESPONSE", f"reader produced no output (rc={p.returncode}) {(p.stderr or '')[-200:]}")
    try: d = json.loads(lines[-1])
    except ValueError: raise IntegrationError("MALFORMED_RESPONSE", f"reader output is not JSON: {lines[-1][:120]}")
    if not isinstance(d, dict) or "ok" not in d: raise IntegrationError("SCHEMA_CHANGED", "reader envelope lacks 'ok'")
    if not d["ok"]:
        msg = str(d.get("error", "")); code = d.get("code")
        if code == "BAD_PARAMS": raise IntegrationError("BAD_PARAMS", msg)
        low = msg.lower()
        if "access denied" in low or "0x80070005" in low or "e_accessdenied" in low: raise IntegrationError("PERMISSION_DENIED", f"Outlook refused access: {msg[:160]}")
        raise IntegrationError("UNAVAILABLE", f"Outlook desktop not reachable (COM): {msg[:160]}", detail=d.get("hresult"), retryable=True)
    return d

def _identity(d, iid):
    accs = [a for a in (d.get("accounts") or []) if isinstance(a, dict)]
    addrs = [str(a.get("address") or "").lower() for a in accs] + [str((d.get("current_user") or {}).get("address") or "").lower()]
    addrs = [a for a in addrs if a and "@" in a]
    exp = (registry.get(iid) or {}).get("expected_identity") or {}
    dom = exp.get("mailbox_domain")
    ident = {"accounts": [a.get("display") for a in accs], "addresses": addrs, "current_user": (d.get("current_user") or {}).get("name"), "verified": None}
    if dom and addrs:
        if not any(a.endswith("@" + dom) for a in addrs): raise IntegrationError("WRONG_TENANT", f"mailbox {addrs[:2]} is not @{dom}")
        ident["verified"] = True
    elif dom: ident["verified"] = False; ident["note"] = "mailbox address not exposed by the profile — identity UNVERIFIED (display names only)"
    return ident

def get_item(entry_id):
    """Read-back of ONE item by EntryID through the fixed read-only reader (used by write verification)."""
    d = _run(["-Op", "get", "-EntryId", str(entry_id)]); _identity(d, "INT-OL-CAL"); return d.get("item")

def probe():
    d = _run(["-Op", "probe"])
    return {"version": d.get("version"), "inbox_count": d.get("inbox_count"), "calendar_count": d.get("calendar_count"), "calendars": d.get("calendars"), "identity": _identity(d, "INT-OL-CAL"), "retrieved_at": d.get("retrieved_at")}

def read(op, params=None, cfg=None, integration_id=None):
    params = params or {}
    iid = integration_id or ("INT-OL-CAL" if op.startswith("calendar") else "INT-OL-MAIL")
    if op not in OPS.get(iid, ()): raise IntegrationError("UNKNOWN_OPERATION", f"{iid} has no operation {op}")
    limit = int(params.get("limit") or 50)
    if limit < 1 or limit > 500: raise IntegrationError("BAD_PARAMS", "limit must be 1..500")
    if op == "calendar.events":
        f = _iso_or_raise(params.get("from"), "from"); t = _iso_or_raise(params.get("to"), "to")
        d = _run(["-Op", "calendar", "-From", f, "-To", t, "-Limit", str(limit), "-PreviewChars", "400"])
        kind = "meeting"; norm = normalize.meeting
    else:
        folder = params.get("folder") or "Inbox"
        if folder not in ("Inbox", "Sent"): raise IntegrationError("BAD_PARAMS", "folder must be Inbox or Sent")
        args = ["-Op", "mail", "-Folder", folder, "-Limit", str(limit), "-PreviewChars", str(int(params.get("preview_chars") or 600))]
        if params.get("since"): args += ["-From", _iso_or_raise(params["since"], "since")]
        if params.get("unread_only"): args += ["-UnreadOnly"]
        if op == "mail.search":
            q = str(params.get("query") or "").strip()
            if not q: raise IntegrationError("BAD_PARAMS", "query missing")
            args += ["-Search", q[:120]]
        d = _run(args); kind = "message"; norm = normalize.message
    if "records" not in d or not isinstance(d["records"], list): raise IntegrationError("SCHEMA_CHANGED", "reader envelope lacks records[]")
    ident = _identity(d, iid)
    recs = []
    for r in d["records"]:
        if not isinstance(r, dict): raise IntegrationError("SCHEMA_CHANGED", "record is not an object")
        recs.append(norm(iid, r))
    notes = []
    if d.get("truncated"): notes.append(f"result truncated at limit {limit} — more items exist")
    upd = max([r.get("source_updated_at") or "" for r in recs] or [""]) or None
    return {"records": recs, "source_updated_at": upd, "identity": ident, "partial": bool(d.get("truncated")), "notes": notes, "kind": kind, "retrieved_at": d.get("retrieved_at")}
