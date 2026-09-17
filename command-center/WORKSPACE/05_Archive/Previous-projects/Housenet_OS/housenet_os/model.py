"""Կանոնական մոդել — առաջադրանք, ակտիվ, մետրիկա."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

TASK_KINDS = ("ritual", "deliverable", "control", "adhoc")
STATUSES = ("todo", "doing", "blocked", "done", "cancelled")
OPEN_STATUSES = ("todo", "doing", "blocked")
SEVERITIES = ("low", "medium", "high", "critical")
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def stable_id(*parts: str) -> str:
    """Կայուն նույնացուցիչ. նույն կանոն + նույն ամսաթիվ = նույն id.

    Սա թույլ է տալիս plan-ը վերագործարկել առանց կրկնօրինակների.
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


@dataclass
class Task:
    id: str
    title: str
    kind: str
    department: str
    owner: str
    due: str  # YYYY-MM-DD
    status: str = "todo"
    rule_id: str = ""
    severity: str = "medium"
    time: str = ""
    duration_min: int = 0
    participants: list = field(default_factory=list)
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    checklist: list = field(default_factory=list)
    channel: str = ""
    notes: str = ""
    depends_on: list = field(default_factory=list)
    created: str = ""
    done_at: str = ""
    escalated_at: str = ""
    escalated_to: str = ""
    source: str = "plan"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES


@dataclass
class Asset:
    """Արտադրվող միավոր — փոստ, վիդեո, script, հաշվետվություն."""

    id: str
    title: str
    department: str
    asset_type: str  # post | video | script | report | email | creative
    channel: str
    owner: str
    publish_at: str  # YYYY-MM-DD
    status: str = "draft"  # draft | review | approved | scheduled | published | killed
    task_id: str = ""
    brief: str = ""
    body: str = ""
    notes: str = ""
    created: str = ""
    published_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Asset":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def severity_sort_key(task: Task) -> tuple:
    return (SEVERITY_ORDER.get(task.severity, 9), task.due, task.department)
