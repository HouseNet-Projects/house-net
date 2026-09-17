# -*- coding: utf-8 -*-
"""ADAPTER INT-TASKS — the canonical task register (Tasks.xlsx) exposed through the same live-information layer as every other
source, so skills reason over ONE normalized shape. Reuses the certified loader (executors.load_tasks): no second parser, no
competing task source. Read-only by construction: this module has no function that opens the workbook for writing."""
import sys, pathlib, datetime
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
from contracts import IntegrationError
import normalize

OPS = ("tasks.list",)

def read(op, params=None, cfg=None):
    params = params or {}
    if op not in OPS: raise IntegrationError("UNKNOWN_OPERATION", f"INT-TASKS has no operation {op}")
    import executors
    path = pathlib.Path(params.get("path") or executors.XLSX)
    if not path.exists(): raise IntegrationError("UNAVAILABLE", f"{path.name} missing")
    try:
        tasks = executors.load_tasks(path)
    except executors.ExecError as e:
        msg = str(e)
        raise IntegrationError("SCHEMA_CHANGED" if "schema drift" in msg or "sheet" in msg else "UNAVAILABLE", msg)
    except Exception as e:
        raise IntegrationError("MALFORMED_RESPONSE", f"{type(e).__name__}: {e}")
    upd = datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    recs = [normalize.task("INT-TASKS", t, upd) for t in tasks]
    if params.get("open_only"): recs = [r for r in recs if r["open"]]
    if params.get("status"): recs = [r for r in recs if r["status"] == params["status"]]
    if params.get("owner"): recs = [r for r in recs if str(params["owner"]).lower() in r["owner"].lower()]
    return {"records": recs, "source_updated_at": upd, "identity": {"path": path.name, "sheet": executors.SHEET}, "partial": False, "notes": []}

def probe(cfg=None):
    return read("tasks.list", {})["identity"]
