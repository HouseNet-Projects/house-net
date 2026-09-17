"""Օրվա և շաբաթվա փաթեթների գեներացում — Markdown."""

from __future__ import annotations

from datetime import date

from .config import Config
from .model import Task

SEV_MARK = {"critical": "‼", "high": "!", "medium": "·", "low": " "}


def _line(cfg: Config, task: Task, show_dept: bool = True) -> str:
    mark = SEV_MARK.get(task.severity, "·")
    who = cfg.org.person_name(task.owner)
    dept = f"[{task.department}] " if show_dept else ""
    when = f" {task.time}" if task.time else ""
    return f"- `{mark}` {dept}**{task.title}**{when} — {who} · ժամկետ {task.due} · `{task.id}`"


def _section(title: str, tasks: list, cfg: Config, empty: str, show_dept: bool = True) -> list:
    out = [f"## {title}", ""]
    if not tasks:
        out += [f"_{empty}_", ""]
        return out
    for task in tasks:
        out.append(_line(cfg, task, show_dept))
    out.append("")
    return out


def daily_brief(cfg: Config, store, snap: dict, department: str = "") -> str:
    today = snap["date"]

    def flt(items):
        return [t for t in items if not department or t.department == department]

    scope = cfg.playbooks[department].title if department else cfg.org.name
    out = [
        f"# {scope} — օրվա փաթեթ",
        f"**{today}**  ·  բաց առաջադրանք՝ {snap['open_total']}",
        "",
    ]

    overdue = flt(snap["overdue"])
    urgent = [t for t in overdue if t.severity in ("critical", "high")]
    if urgent:
        out += [
            "> **Ուշադրություն.** "
            f"{len(urgent)} ուշացած առաջադրանք բարձր կամ կրիտիկական մակարդակի.",
            "",
        ]

    out += _section("Ուշացած", overdue, cfg, "Ուշացած ոչինչ չկա.", not department)
    out += _section("Այսօր", flt(snap["due_today"]), cfg, "Այսօրվա ժամկետ չկա.", not department)
    out += _section("Արգելափակված", flt(snap["blocked"]), cfg, "Արգելափակված ոչինչ չկա.", not department)
    out += _section(
        "Առաջիկա 7 օր", flt(snap["due_week"]), cfg, "Առաջիկա շաբաթում ժամկետ չկա.", not department
    )

    if not department:
        out += ["## Բաժինների պատկեր", "", "| Բաժին | Բաց | Ուշացած |", "|---|---:|---:|"]
        for dept, slot in sorted(
            snap["by_department"].items(), key=lambda kv: (-kv[1]["overdue"], kv[0])
        ):
            title = cfg.playbooks.get(dept).title if dept in cfg.playbooks else dept
            out.append(f"| {title} | {slot['open']} | {slot['overdue']} |")
        out.append("")

    gaps = store.meta.get("last_check", {}).get("data_gaps", [])
    if gaps:
        out += ["## Տվյալի բացեր", "", "_Այս մետրիկները դեռ միացված չեն — հսկիչները կույր են._", ""]
        for gap in gaps:
            out.append(f"- {gap}")
        out.append("")

    return "\n".join(out)


def weekly_pack(cfg: Config, store, snap: dict, sla: dict) -> str:
    out = [
        f"# {cfg.org.name} — շաբաթվա փաթեթ",
        f"**{snap['date']}**",
        "",
        "## Կատարողականություն (վերջին 30 օր)",
        "",
        "| Բաժին | Ընդամենը | Ավարտված | Ժամկետում | Ավարտ % | Ժամկետում % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for dept, slot in sorted(sla["departments"].items()):
        title = cfg.playbooks.get(dept).title if dept in cfg.playbooks else dept
        out.append(
            f"| {title} | {slot['total']} | {slot['done']} | {slot['on_time']} | "
            f"{slot['completion_pct']} | {slot['on_time_pct']} |"
        )
    out += ["", "## Ուշացած՝ ըստ կարևորության", ""]
    for task in snap["overdue"][:30]:
        out.append(_line(cfg, task))
    if not snap["overdue"]:
        out.append("_Ուշացած ոչինչ չկա._")
    out.append("")
    return "\n".join(out)
