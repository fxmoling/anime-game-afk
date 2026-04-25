"""Data models for the multi-script orchestrator.

Defines the core structures for tool configuration, execution plans,
scheduling, and run results.
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

class ToolType(str, enum.Enum):
    """How the orchestrator interacts with a tool."""

    CLI = "cli"          # Full CLI with task selection (MAA, ok-ww)
    CLI_REPLAY = "replay" # CLI that replays last config (M9A -d)
    GUI_CLI = "gui_cli"  # CLI that launches GUI then runs (BetterGI)
    HEADLESS = "headless" # Full headless mode (ZZZ -o)
    GENERIC = "generic"  # Any executable, just launch and wait


class CompletionStrategy(str, enum.Enum):
    """How to detect tool completion."""

    PROCESS_EXIT = "process_exit"  # Wait for process to exit
    TIMEOUT = "timeout"            # Kill after timeout
    LOG_WATCH = "log_watch"        # Watch log file for marker


class ToolRunStatus(str, enum.Enum):
    """Status of a single tool execution."""

    PENDING = "pending"
    PREFLIGHT_FAILED = "preflight_failed"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class WaveStatus(str, enum.Enum):
    """Status of a wave (group of parallel tools)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    ABORTED = "aborted"


class PostActionType(str, enum.Enum):
    """Action to take after all waves complete."""

    NOTHING = "nothing"
    KILL_GAMES = "kill_games"
    SHUTDOWN = "shutdown"
    SLEEP = "sleep"


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

@dataclass
class ToolConfig:
    """Registered external automation tool.

    Stored in user_config.yaml under ``orchestrator.tools``.
    """

    tool_id: str                              # "maa", "okww", "bettergi", ...
    display_name: str                         # "MAA (明日方舟)"
    exe_path: str                             # Absolute path to executable
    tool_type: ToolType = ToolType.GENERIC
    working_dir: str | None = None            # cwd for subprocess, default=exe parent
    args_template: list[str] = field(default_factory=list)  # CLI args pattern
    completion: CompletionStrategy = CompletionStrategy.PROCESS_EXIT
    timeout_minutes: int = 30
    enabled: bool = True
    icon: str = ""                            # Icon filename or emoji
    game_process_names: list[str] = field(default_factory=list)  # For kill_games post-action

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "display_name": self.display_name,
            "exe_path": self.exe_path,
            "tool_type": self.tool_type.value,
            "working_dir": self.working_dir,
            "args_template": self.args_template,
            "completion": self.completion.value,
            "timeout_minutes": self.timeout_minutes,
            "enabled": self.enabled,
            "icon": self.icon,
            "game_process_names": self.game_process_names,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ToolConfig:
        return cls(
            tool_id=d["tool_id"],
            display_name=d["display_name"],
            exe_path=d["exe_path"],
            tool_type=ToolType(d.get("tool_type", "generic")),
            working_dir=d.get("working_dir"),
            args_template=d.get("args_template", []),
            completion=CompletionStrategy(d.get("completion", "process_exit")),
            timeout_minutes=d.get("timeout_minutes", 30),
            enabled=d.get("enabled", True),
            icon=d.get("icon", ""),
            game_process_names=d.get("game_process_names", []),
        )


# ---------------------------------------------------------------------------
# Execution Plan
# ---------------------------------------------------------------------------

@dataclass
class ToolRun:
    """One tool execution within a wave."""

    tool_id: str
    timeout_minutes: int = 30
    task_index: int | None = None   # For ok-ww: -t N
    config_name: str | None = None  # For BetterGI: startOneDragon "name"
    extra_args: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"tool_id": self.tool_id, "timeout_minutes": self.timeout_minutes}
        if self.task_index is not None:
            d["task_index"] = self.task_index
        if self.config_name is not None:
            d["config_name"] = self.config_name
        if self.extra_args:
            d["extra_args"] = self.extra_args
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ToolRun:
        return cls(
            tool_id=d["tool_id"],
            timeout_minutes=d.get("timeout_minutes", 30),
            task_index=d.get("task_index"),
            config_name=d.get("config_name"),
            extra_args=d.get("extra_args", []),
        )


@dataclass
class Wave:
    """A group of tools that run in parallel.

    All tools in a wave start simultaneously. The wave completes
    when all tools finish (or timeout).
    """

    tools: list[ToolRun] = field(default_factory=list)
    label: str = ""  # "步骤 1", user-facing label

    def to_dict(self) -> dict[str, Any]:
        return {
            "tools": [t.to_dict() for t in self.tools],
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Wave:
        return cls(
            tools=[ToolRun.from_dict(t) for t in d.get("tools", [])],
            label=d.get("label", ""),
        )


@dataclass
class PostAction:
    """Action to execute after all waves complete."""

    action_type: PostActionType = PostActionType.NOTHING
    process_names: list[str] = field(default_factory=list)  # For KILL_GAMES
    delay_seconds: int = 120  # For SHUTDOWN/SLEEP

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "process_names": self.process_names,
            "delay_seconds": self.delay_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PostAction:
        return cls(
            action_type=PostActionType(d.get("action_type", "nothing")),
            process_names=d.get("process_names", []),
            delay_seconds=d.get("delay_seconds", 120),
        )


@dataclass
class RunPlan:
    """Complete execution plan: sequential waves of parallel tools."""

    name: str = "每日任务"
    waves: list[Wave] = field(default_factory=list)
    post_action: PostAction = field(default_factory=PostAction)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "waves": [w.to_dict() for w in self.waves],
            "post_action": self.post_action.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RunPlan:
        return cls(
            name=d.get("name", "每日任务"),
            waves=[Wave.from_dict(w) for w in d.get("waves", [])],
            post_action=PostAction.from_dict(d.get("post_action", {})),
        )

    @property
    def total_tools(self) -> int:
        return sum(len(w.tools) for w in self.waves)


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

@dataclass
class ScheduleEntry:
    """Cron-like schedule that triggers a RunPlan."""

    schedule_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "每日凌晨任务"
    cron_expr: str = "0 4 * * *"  # 4:00 AM daily
    plan: RunPlan = field(default_factory=RunPlan)
    enabled: bool = True
    last_run: str | None = None     # ISO timestamp
    next_run: str | None = None     # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "cron_expr": self.cron_expr,
            "plan": self.plan.to_dict(),
            "enabled": self.enabled,
            "last_run": self.last_run,
            "next_run": self.next_run,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScheduleEntry:
        return cls(
            schedule_id=d.get("schedule_id", uuid.uuid4().hex[:8]),
            name=d.get("name", "每日凌晨任务"),
            cron_expr=d.get("cron_expr", "0 4 * * *"),
            plan=RunPlan.from_dict(d.get("plan", {})),
            enabled=d.get("enabled", True),
            last_run=d.get("last_run"),
            next_run=d.get("next_run"),
        )


# ---------------------------------------------------------------------------
# Run Results (runtime, not persisted in config)
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Result of a single tool execution."""

    tool_id: str
    status: ToolRunStatus = ToolRunStatus.PENDING
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str = ""
    log_tail: str = ""  # Last N lines of output

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class WaveResult:
    """Result of a wave execution."""

    wave_index: int
    status: WaveStatus = WaveStatus.PENDING
    tool_results: list[ToolResult] = field(default_factory=list)


@dataclass
class RunResult:
    """Result of a complete RunPlan execution."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    plan_name: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    wave_results: list[WaveResult] = field(default_factory=list)
    post_action_success: bool = True
    aborted: bool = False
    abort_reason: str = ""

    @property
    def success(self) -> bool:
        return all(
            tr.status == ToolRunStatus.SUCCESS
            for wr in self.wave_results
            for tr in wr.tool_results
        ) and not self.aborted
