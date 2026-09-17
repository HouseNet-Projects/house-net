"""Կալենդարի արտահանում — .ics (Google Calendar / Outlook)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .config import Config


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """RFC 5545 — տողերը ծալվում են 75 օկտետից հետո."""
    raw = line.encode("utf-8")
    if len(raw) <= 73:
        return line
    chunks, current = [], b""
    for ch in line:
        enc = ch.encode("utf-8")
        if len(current) + len(enc) > 73:
            chunks.append(current.decode("utf-8"))
            current = b" " + enc
        else:
            current += enc
    chunks.append(current.decode("utf-8"))
    return "\r\n".join(chunks)


def to_ics(cfg: Config, tasks: list, calendar_name: str = "") -> str:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    name = calendar_name or f"{cfg.org.name} Ops"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Housenet OS//AM",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_esc(name)}",
        f"X-WR-TIMEZONE:{cfg.org.timezone}",
    ]

    for task in tasks:
        due = date.fromisoformat(task.due)
        owner = cfg.org.person_name(task.owner)
        dept = cfg.playbooks[task.department].title if task.department in cfg.playbooks else task.department

        desc_parts = [f"Բաժին: {dept}", f"Տեր: {owner}", f"Կարգավիճակ: {task.status}"]
        if task.inputs:
            desc_parts.append("Մուտք: " + "; ".join(task.inputs))
        if task.outputs:
            desc_parts.append("Ելք: " + "; ".join(task.outputs))
        if task.checklist:
            desc_parts.append("Ստուգաթերթ: " + "; ".join(task.checklist))
        desc_parts.append(f"ID: {task.id}")

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{task.id}@housenet-os")
        lines.append(f"DTSTAMP:{stamp}Z")

        if task.time:
            hh, mm = (task.time.split(":") + ["00"])[:2]
            start = datetime(due.year, due.month, due.day, int(hh), int(mm))
            end = start + timedelta(minutes=task.duration_min or 30)
            lines.append(f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}")
            lines.append(f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}")
        else:
            lines.append(f"DTSTART;VALUE=DATE:{due.strftime('%Y%m%d')}")
            lines.append(f"DTEND;VALUE=DATE:{(due + timedelta(days=1)).strftime('%Y%m%d')}")

        lines.append(f"SUMMARY:{_esc(task.title)}")
        lines.append(f"DESCRIPTION:{_esc(chr(10).join(desc_parts))}")
        lines.append(f"CATEGORIES:{_esc(dept)}")
        if task.severity in ("critical", "high"):
            lines.append("PRIORITY:1")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
