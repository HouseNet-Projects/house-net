"""Հսկիչ կանոններ — շեմային ստուգում մետրիկների վրա → ուղղիչ առաջադրանք."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import Config
from .model import Task, stable_id
from .planner import resolve_owner

OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def load_metrics(path: Path) -> dict:
    """Մետրիկները գալիս են տվյալի շերտից (CRM/billing connector).

    Բացակայող ֆայլը սխալ չէ — պարզապես նշանակում է, որ դեռ միացված չէ.
    """
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_controls(cfg: Config, store, metrics: dict, today: date) -> dict:
    issues: list[str] = []
    fired: list[Task] = []
    gaps: list[str] = []
    evaluated = 0

    for dept, pb in cfg.playbooks.items():
        for rule in pb.controls:
            rid = rule.get("id", f"{dept}.control")
            metric = rule.get("metric", "")
            op = rule.get("op", ">")
            threshold = rule.get("threshold", 0)

            if op not in OPS:
                issues.append(f"Անհայտ op '{op}' կանոնում '{rid}'")
                continue

            if metric not in metrics:
                gaps.append(f"{dept}: '{metric}' (կանոն {rid})")
                continue

            evaluated += 1
            value = metrics[metric]
            try:
                breached = OPS[op](value, threshold)
            except TypeError:
                issues.append(f"Չհամեմատվող արժեք '{metric}'={value!r} կանոնում '{rid}'")
                continue

            if not breached:
                continue

            owner = resolve_owner(cfg, rule.get("owner_role", ""), issues)
            due = today + timedelta(days=int(rule.get("due_in_days", 1)))
            task = Task(
                id=stable_id(rid, today.isoformat()),
                title=f"{rule.get('title', rid)} — {metric}={value} (շեմ {op} {threshold})",
                kind="control",
                department=dept,
                owner=owner,
                due=due.isoformat(),
                rule_id=rid,
                severity=rule.get("severity", "high"),
                outputs=[rule.get("action", "")] if rule.get("action") else [],
                checklist=list(rule.get("checklist", [])),
                notes=rule.get("notes", ""),
                created=datetime.now().isoformat(timespec="seconds"),
                source="control",
            )
            if store.upsert_task(task):
                fired.append(task)

    return {
        "evaluated": evaluated,
        "fired": [t.to_dict() for t in fired],
        "data_gaps": sorted(set(gaps)),
        "issues": sorted(set(issues)),
    }
