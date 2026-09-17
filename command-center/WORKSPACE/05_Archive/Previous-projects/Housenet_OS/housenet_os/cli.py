"""Housenet OS — հրամանային տող."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from . import __version__, brief, calendar_out, config, controls, planner, tracker
from .store import Store

ROOT = Path(__file__).resolve().parents[1]


def _load(root: Path):
    cfg = config.load(root)
    store = Store(root / "data" / "state.json")
    return cfg, store


def _today(value: str | None) -> date:
    return date.fromisoformat(value) if value else date.today()


def _write_out(root: Path, name: str, text: str) -> Path:
    path = root / "out" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------- հրամաններ


def cmd_doctor(args) -> int:
    root = Path(args.root)
    try:
        cfg = config.load(root)
    except Exception as exc:
        print(f"ՁԱԽՈՂՈՒՄ: {exc}")
        return 1

    print(f"Կազմակերպություն : {cfg.org.name}  ({cfg.org.timezone})")
    print(f"Բաժիններ         : {len(cfg.playbooks)}")
    print(f"Մարդիկ           : {len(cfg.org.people)}")
    print()

    problems = 0
    used_roles: set[str] = set()
    for dept, pb in cfg.playbooks.items():
        counts = (len(pb.rituals), len(pb.deliverables), len(pb.controls))
        print(f"  {dept:<12} {pb.title:<34} ռիթմ {counts[0]:>2} · արտադրանք {counts[1]:>2} · հսկիչ {counts[2]:>2}")
        for rule in pb.rituals + pb.deliverables + pb.controls:
            for key in ("owner_role", "approver_role"):
                if rule.get(key):
                    used_roles.add(rule[key])
            used_roles.update(rule.get("participants", []))
            if not rule.get("id"):
                print(f"      ! կանոն առանց id ({dept})")
                problems += 1

    missing = sorted(r for r in used_roles if r not in cfg.org.roles)
    if missing:
        print()
        print("Չվերագրված դերեր (առաջադրանքները կմնան UNASSIGNED):")
        for role in missing:
            print(f"  - {role}")
        problems += len(missing)

    orphan = sorted(r for r in cfg.org.roles if r not in used_roles)
    if orphan:
        print()
        print("Դերեր, որոնք ոչ մի կանոն չեն օգտագործում:")
        for role in orphan:
            print(f"  - {role}")

    print()
    print("Արդյունք:", "ԼԱՎ" if problems == 0 else f"{problems} խնդիր")
    return 0


def cmd_plan(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    if args.month:
        year, month = (int(x) for x in args.month.split("-"))
    else:
        now = date.today()
        year, month = now.year, now.month

    start_from = _today(args.date) if args.from_today else None
    result = planner.plan_month(cfg, store, year, month, start_from=start_from)
    store.meta["last_plan"] = {"month": result["month"], "at": datetime.now().isoformat(timespec="seconds")}
    store.save()

    print(f"Պլան {result['month']}: +{result['tasks_created']} առաջադրանք, +{result['assets_created']} ակտիվ")
    for dept, count in sorted(result["per_department"].items(), key=lambda kv: -kv[1]):
        title = cfg.playbooks[dept].title
        print(f"  {dept:<12} {title:<34} {count:>4}")
    if result["issues"]:
        print("\nԽնդիրներ:")
        for issue in result["issues"]:
            print(f"  ! {issue}")
    return 0


def cmd_check(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    metrics = controls.load_metrics(root / "data" / "metrics.json")
    today = _today(args.date)

    result = controls.run_controls(cfg, store, metrics, today)
    store.meta["last_check"] = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "evaluated": result["evaluated"],
        "data_gaps": result["data_gaps"],
    }
    store.save()

    print(f"Ստուգված հսկիչներ: {result['evaluated']} · նոր ահազանգ: {len(result['fired'])}")
    for task in result["fired"]:
        print(f"  [{task['severity']}] {task['department']}: {task['title']}")
    if result["data_gaps"]:
        print(f"\nՏվյալի բացեր ({len(result['data_gaps'])}) — այս հսկիչները կույր են:")
        for gap in result["data_gaps"]:
            print(f"  - {gap}")
    if result["issues"]:
        print("\nԽնդիրներ:")
        for issue in result["issues"]:
            print(f"  ! {issue}")
    return 0


def cmd_brief(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    today = _today(args.date)
    snap = tracker.snapshot(store, today)

    if args.dept and args.dept not in cfg.playbooks:
        print(f"Անհայտ բաժին '{args.dept}'. Հասանելի: {', '.join(sorted(cfg.playbooks))}")
        return 1

    text = brief.daily_brief(cfg, store, snap, department=args.dept or "")
    suffix = f"-{args.dept}" if args.dept else ""
    path = _write_out(root, f"brief-{today.isoformat()}{suffix}.md", text)

    if args.all_departments:
        for dept in sorted(cfg.playbooks):
            dept_text = brief.daily_brief(cfg, store, snap, department=dept)
            _write_out(root, f"brief-{today.isoformat()}-{dept}.md", dept_text)
        print(f"Գրվել է {len(cfg.playbooks)} բաժնի փաթեթ → out/")

    print(text if not args.quiet else f"Գրված է: {path}")
    return 0


def cmd_weekly(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    today = _today(args.date)
    snap = tracker.snapshot(store, today)
    sla = tracker.sla_report(cfg, store, today, days=args.days)
    text = brief.weekly_pack(cfg, store, snap, sla)
    path = _write_out(root, f"weekly-{today.isoformat()}.md", text)
    print(text if not args.quiet else f"Գրված է: {path}")
    return 0


def cmd_tasks(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    today = _today(args.date)

    items = list(store.tasks.values())
    if args.dept:
        items = [t for t in items if t.department == args.dept]
    if args.status:
        items = [t for t in items if t.status == args.status]
    else:
        items = [t for t in items if t.is_open]
    if args.owner:
        items = [t for t in items if t.owner == args.owner]
    if args.overdue:
        items = [t for t in items if date.fromisoformat(t.due) < today]

    items.sort(key=lambda t: (t.due, t.department))
    if not items:
        print("Ոչինչ չի գտնվել.")
        return 0

    for task in items[: args.limit]:
        who = cfg.org.person_name(task.owner)
        flag = "ՈՒՇ" if date.fromisoformat(task.due) < today and task.is_open else "   "
        print(f"{flag} {task.due}  {task.id}  [{task.department:<10}] {task.title[:64]:<64} {who}")
    if len(items) > args.limit:
        print(f"... ևս {len(items) - args.limit}")
    print(f"\nԸնդամենը: {len(items)}")
    return 0


def cmd_done(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    task = store.tasks.get(args.task_id)
    if not task:
        print(f"Առաջադրանք '{args.task_id}' չգտնվեց.")
        return 1
    task.status = "done"
    task.done_at = _today(args.date).isoformat()
    store.save()
    print(f"Ավարտված: {task.title} ({task.done_at})")
    return 0


def cmd_block(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    task = store.tasks.get(args.task_id)
    if not task:
        print(f"Առաջադրանք '{args.task_id}' չգտնվեց.")
        return 1
    task.status = "blocked"
    task.notes = (task.notes + "\n" if task.notes else "") + f"Արգելափակված: {args.reason}"
    store.save()
    print(f"Արգելափակված: {task.title}")
    return 0


def cmd_escalate(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    today = _today(args.date)
    created = tracker.escalate(cfg, store, today, grace_days=args.grace)
    store.save()
    if not created:
        print("Escalate անելու բան չկա.")
        return 0
    print(f"Escalation: {len(created)}")
    for task in created:
        print(f"  [{task.severity}] {task.department}: {task.title} → {cfg.org.person_name(task.owner)}")
    return 0


def cmd_ics(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    items = [t for t in store.tasks.values() if t.is_open]
    if args.dept:
        items = [t for t in items if t.department == args.dept]
    items.sort(key=lambda t: t.due)
    text = calendar_out.to_ics(cfg, items)
    name = f"housenet{'-' + args.dept if args.dept else ''}.ics"
    path = _write_out(root, name, text)
    print(f"{len(items)} իրադարձություն → {path}")
    return 0


def cmd_status(args) -> int:
    root = Path(args.root)
    cfg, store = _load(root)
    today = _today(args.date)
    snap = tracker.snapshot(store, today)
    print(f"{cfg.org.name} · {today.isoformat()}")
    print(f"  բաց       : {snap['open_total']}")
    print(f"  ուշացած   : {len(snap['overdue'])}")
    print(f"  այսօր     : {len(snap['due_today'])}")
    print(f"  7 օրում   : {len(snap['due_week'])}")
    print(f"  արգելափ.  : {len(snap['blocked'])}")
    if store.meta.get("last_check"):
        print(f"  վերջին ստուգում: {store.meta['last_check']['at']}")
    return 0


def cmd_daily(args) -> int:
    """Ամբողջ առավոտյան ցիկլը մեկ հրամանով."""
    for step in (cmd_check, cmd_escalate, cmd_brief):
        code = step(args)
        if code != 0:
            return code
        print()
    return 0


# ---------------------------------------------------------------- entrypoint


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="housenet", description="Housenet OS — օպերացիոն շարժիչ")
    p.add_argument("--root", default=str(ROOT), help="Նախագծի արմատը")
    p.add_argument("--version", action="version", version=f"Housenet OS {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, func, help_text):
        sp = sub.add_parser(name, help=help_text)
        sp.set_defaults(func=func)
        sp.add_argument("--date", help="Հղման ամսաթիվ (YYYY-MM-DD)")
        return sp

    add("doctor", cmd_doctor, "Կոնֆիգի ստուգում")

    sp = add("plan", cmd_plan, "Ամսվա պլանի գեներացում")
    sp.add_argument("--month", help="YYYY-MM")
    sp.add_argument(
        "--from-today",
        action="store_true",
        help="Չստեղծել անցյալ ամսաթվերով առաջադրանք (առաջին տեղադրման համար)",
    )

    add("check", cmd_check, "Հսկիչ կանոնների գործարկում")

    sp = add("brief", cmd_brief, "Օրվա փաթեթ")
    sp.add_argument("--dept")
    sp.add_argument("--all-departments", action="store_true")
    sp.add_argument("--quiet", action="store_true")

    sp = add("weekly", cmd_weekly, "Շաբաթվա փաթեթ")
    sp.add_argument("--days", type=int, default=30)
    sp.add_argument("--quiet", action="store_true")

    sp = add("tasks", cmd_tasks, "Առաջադրանքների ցուցակ")
    sp.add_argument("--dept")
    sp.add_argument("--owner")
    sp.add_argument("--status")
    sp.add_argument("--overdue", action="store_true")
    sp.add_argument("--limit", type=int, default=40)

    sp = add("done", cmd_done, "Առաջադրանքը նշել ավարտված")
    sp.add_argument("task_id")

    sp = add("block", cmd_block, "Առաջադրանքը արգելափակել")
    sp.add_argument("task_id")
    sp.add_argument("reason")

    sp = add("escalate", cmd_escalate, "Ուշացածները բարձրացնել")
    sp.add_argument("--grace", type=int, default=2)

    sp = add("ics", cmd_ics, "Կալենդարի արտահանում")
    sp.add_argument("--dept")

    add("status", cmd_status, "Կարճ պատկեր")

    sp = add("daily", cmd_daily, "Առավոտյան ամբողջ ցիկլը")
    sp.add_argument("--dept")
    sp.add_argument("--all-departments", action="store_true")
    sp.add_argument("--quiet", action="store_true")
    sp.add_argument("--grace", type=int, default=2)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except config.ConfigError as exc:
        print(f"Կոնֆիգի սխալ: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
