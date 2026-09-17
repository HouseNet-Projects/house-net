"""Fail-closed runtime boundary for governed Knowledge and Vault reads.

This module is deliberately provider-neutral. It consumes the canonical repositories,
executes their validators, and exposes metadata only; it never becomes a policy store
and never returns secret values.
"""
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path


class DigitalMemoryError(RuntimeError):
    pass


class DependencyUnavailable(DigitalMemoryError):
    pass


class Contradiction(DigitalMemoryError):
    pass


class AccessDenied(DigitalMemoryError):
    pass


_SENSITIVITY = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "RESTRICTED": 3}


class DigitalMemory:
    """Read-only governed memory boundary for Deputy.

    Knowledge is business content, never policy. Vault reads return reference metadata
    and availability only. A failed validator or missing dependency blocks all reads.
    """

    def __init__(self, knowledge_root, vault_root, *, access_classification="INTERNAL"):
        if access_classification not in _SENSITIVITY:
            raise ValueError("invalid access classification")
        self.knowledge = Path(knowledge_root)
        self.vault = Path(vault_root)
        self.access_classification = access_classification
        self._validated = False

    @staticmethod
    def _run_validator(root, command):
        validator = root / "bin" / command
        if not validator.is_file():
            raise DependencyUnavailable(f"validator unavailable: {command}")
        p = subprocess.run([sys.executable, str(validator)], cwd=str(root), text=True,
                           capture_output=True)
        if p.returncode:
            raise DependencyUnavailable(f"{command} failed closed")

    def validate(self):
        if not self.knowledge.is_dir() or not self.vault.is_dir():
            raise DependencyUnavailable("Knowledge or Vault repository unavailable")
        self._run_validator(self.knowledge, "validate-knowledge")
        self._run_validator(self.vault, "validate-vault")
        self._validated = True

    def _ready(self):
        if not self._validated:
            self.validate()

    def _catalog(self):
        try:
            value = json.loads((self.knowledge / "knowledge/index/catalog.json").read_text())
        except (OSError, ValueError) as exc:
            raise DependencyUnavailable("Knowledge catalog unavailable or corrupt") from exc
        if not isinstance(value.get("items"), list):
            raise DependencyUnavailable("Knowledge catalog contract invalid")
        return value

    def _items(self):
        self._ready()
        self._catalog()
        rows = []
        for path in sorted((self.knowledge / "knowledge").glob("canonical/*.json")):
            try:
                row = json.loads(path.read_text())
            except (OSError, ValueError) as exc:
                raise DependencyUnavailable("canonical Knowledge item unreadable") from exc
            if row.get("status") != "canonical":
                continue
            if _SENSITIVITY.get(row.get("sensitivity"), 99) > _SENSITIVITY[self.access_classification]:
                continue
            freshness = row.get("freshness") or {}
            if freshness.get("state") in {"stale", "unverified"}:
                continue
            rows.append(row)
        ids = [r.get("id") for r in rows]
        if len(ids) != len(set(ids)):
            raise Contradiction("multiple canonical Knowledge items claim the same id")
        title_keys = [(r.get("domain"), str(r.get("title", "")).casefold()) for r in rows]
        if len(title_keys) != len(set(title_keys)):
            raise Contradiction("multiple canonical Knowledge items claim the same domain/title")
        return rows

    def search(self, query):
        """Return canonical, current, provenance-bearing items matching query."""
        q = str(query or "").casefold().strip()
        return [self._public(r) for r in self._items()
                if not q or q in str(r.get("title", "")).casefold()
                or q in str(r.get("domain", "")).casefold()
                or q in str(r.get("id", "")).casefold()]

    def get(self, item_id):
        matches = [r for r in self._items() if r.get("id") == item_id]
        if not matches:
            raise DependencyUnavailable("canonical Knowledge item unavailable")
        return self._public(matches[0])

    @staticmethod
    def _public(row):
        return {k: row[k] for k in
                ("id", "title", "domain", "owner", "status", "source", "effective_date",
                 "supersedes", "superseded_by", "sensitivity", "language", "last_verified", "freshness")
                if k in row}

    def vault_reference(self, reference_id):
        """Return a redacted Vault reference; secret values are never read or returned."""
        self._ready()
        try:
            index = json.loads((self.vault / "vault/index.json").read_text())
        except (OSError, ValueError) as exc:
            raise DependencyUnavailable("Vault index unavailable or corrupt") from exc
        refs = [r for r in index.get("references", []) if r.get("id") == reference_id]
        if len(refs) != 1:
            raise DependencyUnavailable("Vault reference unavailable")
        row = refs[0]
        return {"id": row.get("id"), "purpose": row.get("purpose"),
                "owner_principal": row.get("owner_principal"), "target_system": row.get("target_system"),
                "secret_type": row.get("secret_type"), "sensitivity": row.get("sensitivity"),
                "required_for_bootstrap": bool(row.get("required_for_bootstrap")),
                "recovery_available": bool((row.get("recovery") or {}).get("available")),
                "last_verified": row.get("last_verified"), "available": False,
                "authority": "vault-reference-metadata"}
