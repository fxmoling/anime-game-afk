"""High-level orchestrator manager.

Ties together config management, tool adapters, DAG execution, and
scheduling into a single façade that the API layer calls.
"""
from __future__ import annotations

import asyncio
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from game_scheduler.config_manager import OrchestratorConfigManager
from game_scheduler.models import (
    RunPlan,
    ScheduleEntry,
    ToolConfig,
)
from game_scheduler.runtime.events import EventBus
from game_scheduler.runtime.state import StateStore


# ---------------------------------------------------------------------------
# Common paths for auto-scanning tools
# ---------------------------------------------------------------------------

_SCAN_PATHS: dict[str, list[str]] = {
    "maa": [
        r"C:\Program Files\MAA",
        r"C:\MAA",
        r"D:\MAA",
        os.path.expanduser(r"~\Desktop\MAA"),
    ],
    "m9a": [
        r"C:\Program Files\M9A",
        r"C:\M9A",
        r"D:\M9A",
        os.path.expanduser(r"~\Desktop\M9A"),
    ],
    "okww": [
        r"C:\Program Files\ok-ww",
        r"C:\ok-ww",
        r"D:\ok-ww",
        os.path.expanduser(r"~\Desktop\ok-ww"),
    ],
    "bettergi": [
        r"C:\Program Files\BetterGI",
        r"C:\BetterGI",
        r"D:\BetterGI",
        os.path.expanduser(r"~\Desktop\BetterGI"),
    ],
    "zzz": [
        r"C:\Program Files\ZZZeroHelper",
        r"C:\ZZZeroHelper",
        r"D:\ZZZeroHelper",
        os.path.expanduser(r"~\Desktop\ZZZeroHelper"),
    ],
    "aether": [
        r"C:\Program Files\aether-gazer-afk",
        r"C:\aether-gazer-afk",
        r"D:\aether-gazer-afk",
        os.path.expanduser(r"~\Desktop\aether-gazer-afk"),
    ],
}

_SCAN_EXES: dict[str, list[str]] = {
    "maa": ["MAA.exe", "MaaCore.exe"],
    "m9a": ["M9A.exe", "m9a.exe"],
    "okww": ["ok-ww.exe"],
    "bettergi": ["BetterGI.exe", "BetterGenshinImpact.exe"],
    "zzz": ["ZZZeroHelper.exe"],
    "aether": ["aether-gazer-afk.exe"],
}


# ---------------------------------------------------------------------------
# OrchestratorRunManager
# ---------------------------------------------------------------------------

class OrchestratorRunManager:
    """High-level orchestrator manager.

    Provides the interface that the API layer calls.
    Manages the lifecycle of scheduled and manual runs.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config = OrchestratorConfigManager(config_path)
        self._state = StateStore("data/orchestrator_state.json")
        self._bus = EventBus()
        self._scheduler: Any = None
        self._current_executor: Any = None
        self._run_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        """Populate tool registry with defaults if empty."""
        existing = self._config.get_tools()
        if existing:
            return
        for tool in self._config.get_default_tools():
            self._config.save_tool(tool)
        logger.info("Populated default tool presets")

    def _create_executor(self) -> Any:
        """Build a new :class:`DagExecutor` from current config."""
        from game_scheduler.adapters import get_adapter
        from game_scheduler.dag_executor import DagExecutor

        tools = self._config.get_tools()
        registry = {t.tool_id: t for t in tools}
        adapters = {t.tool_id: get_adapter(t.tool_id) for t in tools}
        return DagExecutor(registry, adapters, self._state, self._bus)

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def get_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._config.get_tools()]

    def save_tool(self, tool_dict: dict[str, Any]) -> dict[str, Any]:
        try:
            tool = ToolConfig.from_dict(tool_dict)
            self._config.save_tool(tool)
            return {"ok": True, "tool_id": tool.tool_id}
        except Exception as exc:
            logger.exception("Failed to save tool")
            return {"ok": False, "error": str(exc)}

    def remove_tool(self, tool_id: str) -> dict[str, Any]:
        removed = self._config.remove_tool(tool_id)
        if removed:
            return {"ok": True}
        return {"ok": False, "error": f"Tool {tool_id!r} not found"}

    def scan_tools(self) -> list[dict[str, Any]]:
        """Scan common paths for installed tools."""
        found: list[dict[str, Any]] = []
        defaults = {t.tool_id: t for t in self._config.get_default_tools()}

        for tool_id, dirs in _SCAN_PATHS.items():
            exe_names = _SCAN_EXES.get(tool_id, [])
            for base_dir in dirs:
                base = Path(base_dir)
                if not base.exists():
                    continue
                for exe_name in exe_names:
                    exe_path = base / exe_name
                    if exe_path.is_file():
                        template = defaults.get(tool_id)
                        if template:
                            d = template.to_dict()
                            d["exe_path"] = str(exe_path)
                            found.append(d)
                            logger.info("Scanned tool: {} at {}", tool_id, exe_path)
                        break
        return found

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def get_schedules(self) -> list[dict[str, Any]]:
        schedules = self._config.get_schedules()
        result: list[dict[str, Any]] = []
        for entry in schedules:
            d = entry.to_dict()
            from game_scheduler.scheduler import _next_fire_time

            nxt = _next_fire_time(entry.cron_expr)
            d["next_run"] = nxt.isoformat() if nxt else None
            result.append(d)
        return result

    def save_schedule(self, schedule_dict: dict[str, Any]) -> dict[str, Any]:
        try:
            normalized = self._normalize_schedule_input(schedule_dict)
            entry = ScheduleEntry.from_dict(normalized)
            self._config.save_schedule(entry)
            return {"ok": True, "id": entry.schedule_id}
        except Exception as exc:
            logger.exception("Failed to save schedule")
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _normalize_schedule_input(d: dict[str, Any]) -> dict[str, Any]:
        """Translate frontend schedule format → ScheduleEntry dict."""
        if "plan" in d and "waves" in d.get("plan", {}):
            return d

        schedule_id = d.get("id") or d.get("schedule_id") or uuid.uuid4().hex[:8]

        time_str = d.get("time", "04:00")
        parts = time_str.split(":")
        hour = int(parts[0]) if len(parts) >= 1 else 4
        minute = int(parts[1]) if len(parts) >= 2 else 0

        days = d.get("days", [])
        interval_hours = d.get("interval_hours")

        if interval_hours:
            cron_expr = f"{minute} */{interval_hours} * * *"
        elif days and set(days) != {"*"} and len(days) < 7:
            day_map = {"周一": "1", "周二": "2", "周三": "3", "周四": "4",
                       "周五": "5", "周六": "6", "周日": "0",
                       "Mon": "1", "Tue": "2", "Wed": "3", "Thu": "4",
                       "Fri": "5", "Sat": "6", "Sun": "0"}
            day_nums = [day_map.get(d2, d2) for d2 in days]
            cron_expr = f"{minute} {hour} * * {','.join(day_nums)}"
        else:
            cron_expr = f"{minute} {hour} * * *"

        steps = d.get("steps", [])
        waves = []
        for i, step in enumerate(steps):
            tools = []
            for t in step.get("tools", []):
                tr: dict[str, Any] = {
                    "tool_id": t["tool_id"],
                    "timeout_minutes": t.get("timeout_min", t.get("timeout_minutes", 30)),
                }
                if t.get("task_index") is not None:
                    tr["task_index"] = t["task_index"]
                if t.get("config_name"):
                    tr["config_name"] = t["config_name"]
                if t.get("extra_args"):
                    tr["extra_args"] = t["extra_args"]
                tools.append(tr)
            waves.append({"tools": tools, "label": f"步骤 {i + 1}"})

        pa_raw = d.get("post_action", "nothing")
        if isinstance(pa_raw, str):
            post_action = {"action_type": pa_raw, "process_names": [], "delay_seconds": 120}
        elif isinstance(pa_raw, dict):
            post_action = pa_raw
        else:
            post_action = {"action_type": "nothing"}

        return {
            "schedule_id": schedule_id,
            "name": d.get("name", "未命名计划"),
            "cron_expr": cron_expr,
            "plan": {
                "name": d.get("name", "每日任务"),
                "waves": waves,
                "post_action": post_action,
            },
            "enabled": d.get("enabled", False),
        }

    def remove_schedule(self, schedule_id: str) -> dict[str, Any]:
        from game_scheduler.scheduler import unregister_wake_task

        unregister_wake_task(schedule_id)

        removed = self._config.remove_schedule(schedule_id)
        if removed:
            return {"ok": True}
        return {"ok": False, "error": f"Schedule {schedule_id!r} not found"}

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_now(self, schedule_id: str) -> dict[str, Any]:
        for entry in self._config.get_schedules():
            if entry.schedule_id == schedule_id:
                return self.run_plan(entry.plan.to_dict())
        return {"ok": False, "error": f"Schedule {schedule_id!r} not found"}

    def run_plan(self, plan_dict: dict[str, Any]) -> dict[str, Any]:
        """Execute a RunPlan. Non-blocking — runs in a background thread."""
        with self._lock:
            if self._run_thread is not None and self._run_thread.is_alive():
                return {"ok": False, "error": "A run is already in progress"}

            try:
                plan = RunPlan.from_dict(plan_dict)
            except Exception as exc:
                return {"ok": False, "error": f"Invalid plan: {exc}"}

            executor = self._create_executor()
            self._current_executor = executor

            def _run() -> None:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(executor.execute(plan))
                except Exception:
                    logger.exception("Plan execution failed")
                finally:
                    with self._lock:
                        self._current_executor = None

            self._run_thread = threading.Thread(
                target=_run,
                name="orch-manual-run",
                daemon=True,
            )
            self._run_thread.start()
            return {"ok": True, "message": f"Started plan: {plan.name}"}

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if self._current_executor is None:
                return {"ok": False, "error": "No run in progress"}
            self._current_executor.cancel()
            return {"ok": True, "message": "Cancellation requested"}

    def get_run_status(self) -> dict[str, Any]:
        state = self._state.get("orchestrator_run")
        running = (
            self._run_thread is not None
            and self._run_thread.is_alive()
        )
        return {
            "running": running,
            "scheduler_active": self._scheduler is not None and self._scheduler.is_running(),
            "run_state": state,
        }

    # ------------------------------------------------------------------
    # Scheduler lifecycle
    # ------------------------------------------------------------------

    def start_scheduler(self) -> None:
        from game_scheduler.scheduler import Scheduler

        if self._scheduler is not None and self._scheduler.is_running():
            logger.warning("Scheduler already running")
            return

        self._scheduler = Scheduler(self._config, self._create_executor)
        self._scheduler.start()
        logger.info("Orchestrator scheduler started")

    def stop_scheduler(self) -> None:
        if self._scheduler is not None:
            self._scheduler.stop()
            self._scheduler = None
        logger.info("Orchestrator scheduler stopped")
