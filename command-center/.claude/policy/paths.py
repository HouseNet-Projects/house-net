# -*- coding: utf-8 -*-
"""CANONICAL BUSINESS-WORKSPACE PATHS — ONE resolver decides where Gev's business files live.

Two roots, never mixed:
  repository root   Deputy's technical shell — .claude/ (engine), .secure/ (encrypted recovery), .venv/ (regenerated),
                    bootstrap.py, CLAUDE.md, README.md, .gitignore, .gitattributes. Gev never needs to open any of it.
  business root     WORKSPACE/ — Gev's daily surface: 00_Inbox … 05_Archive + Tasks.xlsx · Journal.md · Actions.md.
                    Declared once in workspace_policy.json -> business_root; every resolver reads it from here.

Nothing else in the system may hard-code "01_Active" or "Tasks.xlsx" against the repository root: a second definition is
exactly how a workspace root drifts. Validator, guard, tree manifest, sync, skills, adapters, tools and tests all call in here.
"""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
POLICY_PATH = HERE / "workspace_policy.json"

DEFAULT_BUSINESS_ROOT = "WORKSPACE"
AREAS = ("00_Inbox", "01_Active", "02_Reference", "03_Completed", "04_Sources", "05_Archive")
REGISTERS = ("Tasks.xlsx", "Journal.md", "Actions.md")
INBOX_INPUT = "00_Inbox/Input.md"

_cache = {}

def _policy(pol=None):
    if pol is not None: return pol
    try:
        st = POLICY_PATH.stat().st_mtime_ns
        if _cache.get("mtime") != st:
            _cache["pol"] = json.loads(POLICY_PATH.read_text(encoding="utf-8")); _cache["mtime"] = st
        return _cache["pol"]
    except (OSError, ValueError):
        return None

def root_name(pol=None):
    """The business root folder name. Policy is authoritative; the constant keeps stdlib-only callers (bootstrap) working."""
    p = _policy(pol)
    name = (p or {}).get("business_root") or DEFAULT_BUSINESS_ROOT
    return str(name).strip("/\\") or DEFAULT_BUSINESS_ROOT

def root(repo_root=None, pol=None):
    return pathlib.Path(repo_root or REPO_ROOT) / root_name(pol)

def biz(*rel, repo_root=None, pol=None):
    """Absolute path of a BUSINESS-relative path: biz('01_Active', 'Sales') → <repo>/WORKSPACE/01_Active/Sales."""
    return root(repo_root, pol).joinpath(*[str(r) for r in rel])

def tasks(repo_root=None, pol=None): return biz("Tasks.xlsx", repo_root=repo_root, pol=pol)
def journal(repo_root=None, pol=None): return biz("Journal.md", repo_root=repo_root, pol=pol)
def actions(repo_root=None, pol=None): return biz("Actions.md", repo_root=repo_root, pol=pol)
def inbox_input(repo_root=None, pol=None): return biz(INBOX_INPUT, repo_root=repo_root, pol=pol)

def _norm(rel): return str(rel).replace("\\", "/").strip("/")

def is_business_relative(rel):
    """True for a path expressed relative to the BUSINESS root (01_Active/…, Tasks.xlsx, 00_Inbox/Input.md)."""
    r = _norm(rel); top = r.split("/")[0]
    return top in AREAS or r in REGISTERS

def to_repo(rel, pol=None):
    """BUSINESS-relative → REPOSITORY-relative. Already-prefixed and technical paths pass through unchanged."""
    r = _norm(rel); name = root_name(pol)
    if r == name or r.startswith(name + "/"): return r
    return f"{name}/{r}" if is_business_relative(r) else r

def to_business(rel, pol=None):
    """REPOSITORY-relative → BUSINESS-relative, or None when the path is not inside the business root."""
    r = _norm(rel); name = root_name(pol)
    if r == name: return ""
    if r.startswith(name + "/"): return r[len(name) + 1:]
    return None

def is_inside(rel, pol=None):
    return to_business(rel, pol) is not None

def areas(pol=None):
    """Repository-relative paths of the six business areas, in order."""
    name = root_name(pol)
    return tuple(f"{name}/{a}" for a in AREAS)

def registers(pol=None):
    name = root_name(pol)
    return tuple(f"{name}/{f}" for f in REGISTERS)

def resolve(repo_root, rel, pol=None):
    """Absolute path for a path written either business-relative or repository-relative (business-model sources, manifests)."""
    return pathlib.Path(repo_root) / to_repo(rel, pol)
