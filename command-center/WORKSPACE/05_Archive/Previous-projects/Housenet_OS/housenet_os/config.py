"""Կոնֆիգի բեռնում — կազմակերպություն, թիրախներ, playbook-եր."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"Ֆայլը չկա: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


@dataclass
class Org:
    name: str
    timezone: str
    workweek: list
    holidays: list
    departments: dict  # id -> {title, lead_role, escalates_to}
    people: dict  # id -> {name, role, department, email}
    roles: dict  # role -> person id

    def person_for_role(self, role: str) -> str:
        """Դերից → մարդու id. Չլրացված դերը ձախողում է բացահայտ."""
        pid = self.roles.get(role)
        if not pid:
            raise ConfigError(
                f"Դերը վերագրված չէ ոչ մեկին: '{role}'. Լրացրու config/org.yaml → roles."
            )
        if pid not in self.people:
            raise ConfigError(f"Դեր '{role}' → անհայտ մարդ '{pid}'.")
        return pid

    def person_name(self, pid: str) -> str:
        return self.people.get(pid, {}).get("name", pid)

    def escalation_target(self, department: str) -> str:
        dept = self.departments.get(department, {})
        return dept.get("escalates_to", "ops_head")


@dataclass
class Playbook:
    department: str
    title: str
    kpis: list
    rituals: list
    deliverables: list
    controls: list


@dataclass
class Config:
    root: Path
    org: Org
    targets: dict
    playbooks: dict  # department -> Playbook

    @property
    def departments(self) -> list:
        return list(self.playbooks.keys())


def load(root: Path) -> Config:
    root = Path(root)
    org_raw = _read_yaml(root / "config" / "org.yaml")
    org = Org(
        name=org_raw.get("name", "Housenet"),
        timezone=org_raw.get("timezone", "Asia/Yerevan"),
        workweek=org_raw.get("workweek", ["mon", "tue", "wed", "thu", "fri"]),
        holidays=org_raw.get("holidays", []),
        departments=org_raw.get("departments", {}),
        people=org_raw.get("people", {}),
        roles=org_raw.get("roles", {}),
    )
    targets = _read_yaml(root / "config" / "targets.yaml")

    playbooks: dict[str, Playbook] = {}
    pb_dir = root / "config" / "playbooks"
    if not pb_dir.exists():
        raise ConfigError(f"Playbook-երի պանակը չկա: {pb_dir}")
    for path in sorted(pb_dir.glob("*.yaml")):
        raw = _read_yaml(path)
        dept = raw.get("department") or path.stem
        playbooks[dept] = Playbook(
            department=dept,
            title=raw.get("title", dept),
            kpis=raw.get("kpis", []) or [],
            rituals=raw.get("rituals", []) or [],
            deliverables=raw.get("deliverables", []) or [],
            controls=raw.get("controls", []) or [],
        )
    if not playbooks:
        raise ConfigError("Ոչ մի playbook չգտնվեց.")
    return Config(root=root, org=org, targets=targets, playbooks=playbooks)
