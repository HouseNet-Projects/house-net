"""Պլանավորող — playbook-երից ամսվա առաջադրանքներ և ակտիվներ."""

from __future__ import annotations

from datetime import date, datetime

from .config import Config
from .model import Asset, Task, stable_id
from .schedule import apply_lead_days, expand

UNASSIGNED = "UNASSIGNED"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def resolve_owner(cfg: Config, role: str, issues: list) -> str:
    if not role:
        issues.append("Կանոն առանց owner_role — տերը մնում է չվերագրված.")
        return UNASSIGNED
    try:
        return cfg.org.person_for_role(role)
    except Exception as exc:  # ConfigError
        issues.append(str(exc))
        return UNASSIGNED


def _ritual_task(cfg: Config, dept: str, rule: dict, day: date, issues: list) -> Task:
    rid = rule.get("id", f"{dept}.unnamed")
    owner = resolve_owner(cfg, rule.get("owner_role", ""), issues)
    return Task(
        id=stable_id(rid, day.isoformat()),
        title=rule.get("title", rid),
        kind="ritual",
        department=dept,
        owner=owner,
        due=day.isoformat(),
        rule_id=rid,
        severity=rule.get("severity", "medium"),
        time=rule.get("time", ""),
        duration_min=int(rule.get("duration_min", 0)),
        participants=list(rule.get("participants", [])),
        inputs=list(rule.get("inputs", [])),
        outputs=list(rule.get("outputs", [])),
        checklist=list(rule.get("checklist", [])),
        notes=rule.get("notes", ""),
        created=_now(),
        source="plan",
    )


def _deliverable_tasks(
    cfg: Config, dept: str, rule: dict, day: date, issues: list
) -> tuple[list[Task], list[Asset]]:
    """Արտադրանքը ծնում է երկու առաջադրանք — պատրաստում և թողարկում."""
    rid = rule.get("id", f"{dept}.unnamed")
    owner = resolve_owner(cfg, rule.get("owner_role", ""), issues)
    approver_role = rule.get("approver_role", "")
    approver = resolve_owner(cfg, approver_role, issues) if approver_role else ""
    channels = rule.get("channels") or [rule.get("channel", "")]
    lead = int(rule.get("lead_days", 0))
    asset_type = rule.get("asset_type", "deliverable")

    tasks: list[Task] = []
    assets: list[Asset] = []

    for channel in channels:
        suffix = f" — {channel}" if channel else ""
        asset_id = stable_id("asset", rid, day.isoformat(), channel or "")

        if lead > 0:
            prep_day = apply_lead_days(day, lead, cfg.org.workweek, cfg.org.holidays)
            tasks.append(
                Task(
                    id=stable_id(rid, day.isoformat(), channel or "", "prep"),
                    title=f"Պատրաստել: {rule.get('title', rid)}{suffix}",
                    kind="deliverable",
                    department=dept,
                    owner=owner,
                    due=prep_day.isoformat(),
                    rule_id=rid,
                    severity=rule.get("severity", "medium"),
                    channel=channel or "",
                    inputs=list(rule.get("inputs", [])),
                    outputs=list(rule.get("outputs", [])),
                    checklist=list(rule.get("checklist", [])),
                    notes=rule.get("brief", ""),
                    created=_now(),
                    source="plan",
                )
            )

        publish_task = Task(
            id=stable_id(rid, day.isoformat(), channel or "", "publish"),
            title=f"{rule.get('title', rid)}{suffix}",
            kind="deliverable",
            department=dept,
            owner=approver or owner,
            due=day.isoformat(),
            rule_id=rid,
            severity=rule.get("severity", "medium"),
            time=rule.get("time", ""),
            channel=channel or "",
            checklist=list(rule.get("publish_checklist", [])),
            notes=rule.get("brief", ""),
            created=_now(),
            source="plan",
        )
        if lead > 0:
            publish_task.depends_on = [stable_id(rid, day.isoformat(), channel or "", "prep")]
        tasks.append(publish_task)

        assets.append(
            Asset(
                id=asset_id,
                title=f"{rule.get('title', rid)}{suffix}",
                department=dept,
                asset_type=asset_type,
                channel=channel or "",
                owner=owner,
                publish_at=day.isoformat(),
                task_id=publish_task.id,
                brief=rule.get("brief", ""),
                created=_now(),
            )
        )

    return tasks, assets


def plan_month(cfg: Config, store, year: int, month: int, start_from: date | None = None) -> dict:
    """Գեներացնում է ամսվա բոլոր առաջադրանքները բոլոր բաժինների համար.

    start_from — եթե տրված է, ավելի վաղ ամսաթվերով առաջադրանք չի ստեղծվում.
    Առաջին տեղադրման ժամանակ սա փրկում է կեղծ «ուշացած» պատկերից.
    """
    issues: list[str] = []
    created_tasks = 0
    created_assets = 0
    per_dept: dict[str, int] = {}

    def dates_for(rule: dict) -> list:
        days = expand(rule, year, month, cfg.org.workweek, cfg.org.holidays)
        if start_from:
            days = [d for d in days if d >= start_from]
        return days

    for dept, pb in cfg.playbooks.items():
        count = 0

        for rule in pb.rituals:
            for day in dates_for(rule):
                task = _ritual_task(cfg, dept, rule, day, issues)
                if store.upsert_task(task):
                    created_tasks += 1
                    count += 1

        for rule in pb.deliverables:
            for day in dates_for(rule):
                tasks, assets = _deliverable_tasks(cfg, dept, rule, day, issues)
                for task in tasks:
                    if store.upsert_task(task):
                        created_tasks += 1
                        count += 1
                for asset in assets:
                    if store.upsert_asset(asset):
                        created_assets += 1

        per_dept[dept] = count

    return {
        "month": f"{year:04d}-{month:02d}",
        "tasks_created": created_tasks,
        "assets_created": created_assets,
        "per_department": per_dept,
        "issues": sorted(set(issues)),
    }
