# -*- coding: utf-8 -*-
"""INTEGRATION SECRETS (module int_secrets — never named `secrets`, which would shadow the stdlib) — resolved from the environment or from ~/.command-center/integrations/<INTEGRATION_ID>.json (RESTRICTED,
outside the repository, outside the audit). Values are registered for redaction the moment they are loaded: no envelope, error,
health record, cache file or audit line may carry them (layer.query fails closed with LEAK_PREVENTED if one would).

    env:   CC_INT_B24_WEBHOOK_URL=…            → load_config("INT-B24")["webhook_url"]
    file:  ~/.command-center/integrations/INT-B24.json  {"webhook_url": "…", "portal_domain": "…"}"""
import os, json, pathlib, re

def home_dir():
    return pathlib.Path(os.environ.get("COMMAND_CENTER_HOME") or (pathlib.Path.home() / ".command-center")) / "integrations"

def config_path(integration_id): return home_dir() / f"{integration_id}.json"

_KNOWN = {}            # value → label (never printed)
SECRET_KEY_RX = re.compile(r"(url|token|secret|password|passwd|key|webhook|dsn|connection|credential)", re.I)
BITRIX_URL_RX = re.compile(r"(/rest/\d+/)[A-Za-z0-9]{8,}(/?)")

def load_config(integration_id):
    cfg = {}
    p = config_path(integration_id)
    if p.exists():
        try: cfg.update({k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items()})
        except (OSError, ValueError): pass
    prefix = "CC_" + integration_id.replace("-", "_").upper() + "_"
    for k, v in os.environ.items():
        if k.startswith(prefix) and len(k) > len(prefix): cfg[k[len(prefix):].lower()] = v
    register(cfg, integration_id)
    return cfg

def register(cfg, label="cfg"):
    for k, v in (cfg or {}).items():
        if isinstance(v, str) and len(v) >= 8 and SECRET_KEY_RX.search(k): _KNOWN[v] = f"{label}.{k}"

def redact(text):
    """Replace every known secret value (and any Bitrix webhook code) in text with a marker."""
    t = str(text)
    for v in sorted(_KNOWN, key=len, reverse=True): t = t.replace(v, "<secret>")
    return BITRIX_URL_RX.sub(r"\1<secret>\2", t)

def leaks(obj):
    """Names of known secrets whose VALUE appears anywhere in obj (json-serialized). Empty = clean."""
    blob = json.dumps(obj, ensure_ascii=False, default=str)
    hits = [label for v, label in _KNOWN.items() if v in blob]
    if BITRIX_URL_RX.search(blob) and "<secret>" not in BITRIX_URL_RX.search(blob).group(0): hits.append("bitrix webhook code")
    return hits

def known_count(): return len(_KNOWN)
