"""Pure data models for the game scheduler.

All types are plain dataclasses — no I/O, no side effects.
Each has ``to_dict`` / ``from_dict`` for JSON serialization.
"""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ToolStatus(str, enum.Enum):
    READY = "ready"
    NOT_FOUND = "not_found"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class PostActionKind(str, enum.Enum):
    NOTHING = "nothing"
    KILL_GAMES = "kill_games"
    SHUTDOWN = "shutdown"
    SLEEP = "sleep"


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@dataclass
class ToolInfo:
    """A registered automation tool."""

    tool_id: str
    name: str = ""
    exe_path: str = ""
    install_dir: str = ""
    version: str = ""
    status: ToolStatus = ToolStatus.UNCONFIGURED
    icon: str = "🔧"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "exe_path": self.exe_path,
            "install_dir": self.install_dir,
            "version": self.version,
            "status": self.status.value,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ToolInfo:
        return cls(
            tool_id=d["tool_id"],
            name=d.get("name", ""),
            exe_path=d.get("exe_path", ""),
            install_dir=d.get("install_dir", ""),
            version=d.get("version", ""),
            status=ToolStatus(d.get("status", "unconfigured")),
            icon=d.get("icon", "🔧"),
        )


# ---------------------------------------------------------------------------
# Task / Wave / Plan
# ---------------------------------------------------------------------------

@dataclass
class TaskConfig:
    """What to run for a single tool within a wave."""

    tool_id: str
    timeout_min: int = 30
    cli_args: list[str] = field(default_factory=list)
    tasks_enabled: dict[str, bool] | None = None
    config_overrides: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tool_id": self.tool_id,
            "timeout_min": self.timeout_min,
        }
        if self.cli_args:
            d["cli_args"] = self.cli_args
        if self.tasks_enabled is not None:
            d["tasks_enabled"] = self.tasks_enabled
        if self.config_overrides is not None:
            d["config_overrides"] = self.config_overrides
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskConfig:
        return cls(
            tool_id=d["tool_id"],
            timeout_min=d.get("timeout_min", 30),
            cli_args=d.get("cli_args", []),
            tasks_enabled=d.get("tasks_enabled"),
            config_overrides=d.get("config_overrides"),
        )


@dataclass
class Wave:
    """A group of tasks that run in parallel."""

    tasks: list[TaskConfig] = field(default_factory=list)
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks": [t.to_dict() for t in self.tasks],
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Wave:
        return cls(
            tasks=[TaskConfig.from_dict(t) for t in d.get("tasks", [])],
            label=d.get("label", ""),
        )


@dataclass
class PostAction:
    """What to do after all waves complete."""

    kind: PostActionKind = PostActionKind.NOTHING
    process_names: list[str] = field(default_factory=list)
    delay_seconds: int = 120

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "process_names": self.process_names,
            "delay_seconds": self.delay_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PostAction:
        return cls(
            kind=PostActionKind(d.get("kind", "nothing")),
            process_names=d.get("process_names", []),
            delay_seconds=d.get("delay_seconds", 120),
        )


@dataclass
class Plan:
    """Execution plan: sequential waves of parallel tasks."""

    name: str = "每日任务"
    waves: list[Wave] = field(default_factory=list)
    post_action: PostAction = field(default_factory=PostAction)

    @property
    def total_tasks(self) -> int:
        return sum(len(w.tasks) for w in self.waves)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "waves": [w.to_dict() for w in self.waves],
            "post_action": self.post_action.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Plan:
        return cls(
            name=d.get("name", "每日任务"),
            waves=[Wave.from_dict(w) for w in d.get("waves", [])],
            post_action=PostAction.from_dict(d.get("post_action", {})),
        )


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

def _new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class Schedule:
    """A cron-triggered plan."""

    id: str = field(default_factory=_new_id)
    name: str = "每日凌晨任务"
    cron: str = "0 4 * * *"
    plan: Plan = field(default_factory=Plan)
    enabled: bool = True
    last_run: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cron": self.cron,
            "plan": self.plan.to_dict(),
            "enabled": self.enabled,
            "last_run": self.last_run,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Schedule:
        return cls(
            id=d.get("id", _new_id()),
            name=d.get("name", "每日凌晨任务"),
            cron=d.get("cron", "0 4 * * *"),
            plan=Plan.from_dict(d.get("plan", {})),
            enabled=d.get("enabled", True),
            last_run=d.get("last_run"),
        )


# ---------------------------------------------------------------------------
# Run results (runtime, not persisted in config)
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    """Result of running one tool."""

    tool_id: str
    status: RunStatus = RunStatus.PENDING
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str = ""

    @property
    def duration_s(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "duration_s": self.duration_s,
            "error": self.error,
        }


@dataclass
class WaveResult:
    """Result of one wave (parallel group)."""

    index: int
    tasks: list[TaskResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(t.status == RunStatus.SUCCESS for t in self.tasks)


@dataclass
class RunResult:
    """Complete result of a plan execution."""

    run_id: str = field(default_factory=_new_id)
    plan_name: str = ""
    waves: list[WaveResult] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    aborted: bool = False

    @property
    def success(self) -> bool:
        return not self.aborted and all(w.all_ok for w in self.waves)
