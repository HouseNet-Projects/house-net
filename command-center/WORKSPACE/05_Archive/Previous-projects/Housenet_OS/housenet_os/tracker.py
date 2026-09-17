"""Հսկիչ շերտ — ուշացումներ, escalation, օրվա պատկեր."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .config import Config
from .model import Task, severity_sort_key, stable_id


def _d(value: str) -> date:
    return date.fromisoformat(value)


def snapshot(store, today: date) -> dict:
    overdue, due_today, due_week, blocked = [], [], [], []
    week_end = today + timedelta(days=7)

    for task in store.open_tasks():
        due = _d(task.due)
        if task.status == "blocked":
            blocked.append(task)
        if due < today:
            overdue.append(task)
        elif due == today:
            due_today.append(task)
        elif due <= week_end:
            due_week.append(task)

    by_dept: dict[str, dict] = {}
    for task in store.open_tasks():
        slot = by_dept.setdefault(task.department, {"open": 0, "overdue": 0})
        slot["open"] += 1
        if _d(task.due) < today:
            slot["overdue"] += 1

    return {
        "date": today.isoformat(),
        "overdue": sorted(overdue, key=severity_sort_key),
        "due_today": sorted(due_today, key=severity_sort_key),
        "due_week": sorted(due_week, key=severity_sort_key),
        "blocked": sorted(blocked, key=severity_sort_key),
        "by_department": by_dept,
        "open_total": len(store.open_tasks()),
    }


def escalate(cfg: Config, store, today: date, grace_days: int = 2) -> list[Task]:
    """Ուշացած առաջադրանքը grace_days հետո բարձրանում է բաժնի ղեկավարին."""
    created: list[Task] = []
    for task in list(store.open_tasks()):
        if task.escalated_at or task.source == "escalation":
            continue
        overdue_days = (today - _d(task.due)).days
        if overdue_days < grace_days:
            continue

        role = cfg.org.escalation_target(task.department)
        try:
            target = cfg.org.person_for_role(role)
        except Exception:
            target = "UNASSIGNED"

        task.escalated_at = today.isoformat()
        task.escalated_to = target

        esc = Task(
            id=stable_id("escalation", task.id, today.isoformat()),
            title=f"Escalation: «{task.title}» ուշացած է {overdue_days} օր",
            kind="control",
            department=task.department,
            owner=target,
            due=(today + timedelta(days=1)).isoformat(),
            rule_id="core.escalation",
            severity="high" if overdue_days < 5 else "critical",
            inputs=[f"Սկզբնական տեր: {cfg.org.person_name(task.owner)}", f"Ժամկետ էր: {task.due}"],
            outputs=["Որոշում: ավարտել, վերանշանակել, կամ չեղարկել հիմնավորմամբ"],
            depends_on=[task.id],
            created=datetime.now().isoformat(timespec="seconds"),
            source="escalation",
        )
        if store.upsert_task(esc):
            created.append(esc)
    return created


def sla_report(cfg: Config, store, today: date, days: int = 30) -> dict:
    """Ինչքա՞ն է կատարողականը վերջին N օրում — ըստ բաժնի."""
    since = today - timedelta(days=days)
    stats: dict[str, dict] = {}
    for task in store.tasks.values():
        due = _d(task.due)
        if due < since or due > today:
            continue
        slot = stats.setdefault(task.department, {"total": 0, "done": 0, "on_time": 0, "late": 0})
        slot["total"] += 1
        if task.status != "done":
            continue
        slot["done"] += 1
        if task.done_at and _d(task.done_at[:10]) <= due:
            slot["on_time"] += 1
        else:
            slot["late"] += 1

    for slot in stats.values():
        slot["completion_pct"] = round(100 * slot["done"] / slot["total"], 1) if slot["total"] else 0.0
        slot["on_time_pct"] = round(100 * slot["on_time"] / slot["done"], 1) if slot["done"] else 0.0
    return {"window_days": days, "since": since.isoformat(), "departments": stats}
