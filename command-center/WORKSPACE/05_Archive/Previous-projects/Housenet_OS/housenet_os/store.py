"""Վիճակի պահոց — JSON, ատոմային գրառմամբ."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .model import Asset, Task


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.tasks: dict[str, Task] = {}
        self.assets: dict[str, Asset] = {}
        self.meta: dict = {}
        self.load()

    # ---------- I/O ----------

    def load(self) -> None:
        if not self.path.exists():
            self.meta = {"schema": 1}
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.meta = raw.get("meta", {"schema": 1})
        self.tasks = {t["id"]: Task.from_dict(t) for t in raw.get("tasks", [])}
        self.assets = {a["id"]: Asset.from_dict(a) for a in raw.get("assets", [])}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": self.meta,
            "tasks": [t.to_dict() for t in self.tasks.values()],
            "assets": [a.to_dict() for a in self.assets.values()],
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # ---------- առաջադրանքներ ----------

    def upsert_task(self, task: Task) -> bool:
        """Վերադարձնում է True, եթե նոր առաջադրանք է ավելացվել."""
        existing = self.tasks.get(task.id)
        if existing is None:
            self.tasks[task.id] = task
            return True
        # Գործող առաջադրանքի կարգավիճակը երբեք չի վերագրվում պլանից.
        existing.title = task.title
        existing.inputs = task.inputs
        existing.outputs = task.outputs
        existing.checklist = task.checklist
        existing.participants = task.participants
        existing.severity = task.severity
        return False

    def open_tasks(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.is_open]

    def by_department(self, department: str) -> list[Task]:
        return [t for t in self.tasks.values() if t.department == department]

    # ---------- ակտիվներ ----------

    def upsert_asset(self, asset: Asset) -> bool:
        if asset.id in self.assets:
            existing = self.assets[asset.id]
            existing.title = asset.title
            existing.brief = asset.brief
            return False
        self.assets[asset.id] = asset
        return True
