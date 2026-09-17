"""Ռիթմի ընդլայնում — cadence → կոնկրետ ամսաթվեր."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

CADENCES = (
    "daily",
    "workdays",
    "weekly",
    "biweekly",
    "monthly",
    "quarterly",
    "month_start",
    "month_end",
    "none",
)


class ScheduleError(Exception):
    pass


def month_range(year: int, month: int) -> list[date]:
    last = calendar.monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, last + 1)]


def is_workday(day: date, workweek: list, holidays: set) -> bool:
    if day.isoformat() in holidays:
        return False
    allowed = {WEEKDAYS[w] for w in workweek if w in WEEKDAYS}
    return day.weekday() in allowed


def shift_to_workday(day: date, workweek: list, holidays: set, forward: bool = False) -> date:
    """Ոչ աշխատանքային օրը տեղափոխում է մոտակա աշխատանքայինին."""
    step = 1 if forward else -1
    guard = 0
    while not is_workday(day, workweek, holidays):
        day = day + timedelta(days=step)
        guard += 1
        if guard > 14:
            return day
    return day


def expand(rule: dict, year: int, month: int, workweek: list, holidays: list) -> list[date]:
    """Կանոնի cadence-ը վերածում է ամսվա ամսաթվերի ցուցակի."""
    cadence = rule.get("cadence", "none")
    if cadence not in CADENCES:
        raise ScheduleError(f"Անհայտ cadence '{cadence}' կանոնում '{rule.get('id')}'")

    hol = set(holidays or [])
    days = month_range(year, month)

    if cadence == "none":
        return []

    if cadence == "daily":
        return days

    if cadence == "workdays":
        return [d for d in days if is_workday(d, workweek, hol)]

    if cadence in ("weekly", "biweekly"):
        wd = rule.get("weekday", "mon")
        if wd not in WEEKDAYS:
            raise ScheduleError(f"Անհայտ weekday '{wd}' կանոնում '{rule.get('id')}'")
        hits = [d for d in days if d.weekday() == WEEKDAYS[wd]]
        if cadence == "biweekly":
            hits = hits[::2]
        return hits

    if cadence == "monthly":
        dom = int(rule.get("day", 1))
        last = calendar.monthrange(year, month)[1]
        dom = min(max(dom, 1), last)
        return [shift_to_workday(date(year, month, dom), workweek, hol, forward=True)]

    if cadence == "quarterly":
        if month not in (int(m) for m in rule.get("months", [1, 4, 7, 10])):
            return []
        dom = int(rule.get("day", 1))
        last = calendar.monthrange(year, month)[1]
        dom = min(max(dom, 1), last)
        return [shift_to_workday(date(year, month, dom), workweek, hol, forward=True)]

    if cadence == "month_start":
        offset = int(rule.get("offset", 0))
        target = date(year, month, 1) + timedelta(days=offset)
        if target.month != month:
            return []
        return [shift_to_workday(target, workweek, hol, forward=True)]

    if cadence == "month_end":
        offset = int(rule.get("offset", 0))
        last = calendar.monthrange(year, month)[1]
        target = date(year, month, last) - timedelta(days=offset)
        if target.month != month:
            return []
        return [shift_to_workday(target, workweek, hol, forward=False)]

    return []


def apply_lead_days(due: date, lead_days: int, workweek: list, holidays: list) -> date:
    """Պատրաստման առաջադրանքի ժամկետը — հրապարակումից N օր առաջ."""
    if not lead_days:
        return due
    target = due - timedelta(days=int(lead_days))
    return shift_to_workday(target, workweek, set(holidays or []), forward=False)
