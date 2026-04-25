"""API handlers: all methods exposed to the frontend."""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from loguru import logger

from gs.config.base import NullAdapter
from gs.config.maa import MaaConfigAdapter
from gs.config.okww import OkwwConfigAdapter
from gs.config.bettergi import BettergiConfigAdapter
from gs.config.m9a import M9aConfigAdapter
from gs.config.zzz import ZzzConfigAdapter
from gs.core.models import Plan, Schedule, ToolInfo
from gs.discovery.scanner import ToolScanner
from gs.execution.dag import DagExecutor
from gs.execution.post import run_post_action
from gs.schedule.scheduler import Scheduler
from gs.store.settings import Settings


# Config adapters by tool_id
_ADAPTERS = {
    "maa": MaaConfigAdapter(),
    "okww": OkwwConfigAdapter(),
    "bettergi": BettergiConfigAdapter(),
    "m9a": M9aConfigAdapter(),
    "zzz": ZzzConfigAdapter(),
}
_NULL = NullAdapter()


class ApiHandlers:
    """All methods callable from the frontend (pywebview js_api)."""

    def __init__(self) -> None:
        self._settings = Settings()
        self._scanner = ToolScanner()
        self._executor: DagExecutor | None = None
        self._run_thread: threading.Thread | None = None
        self._scheduler = Scheduler(
            get_schedules=self._settings.get_schedules,
            on_fire=self._on_schedule_fire,
        )

    # ------------------------------------------------------------------
    # Tool discovery
    # ------------------------------------------------------------------

    def scan_tools(self) -> list[dict[str, Any]]:
        """Scan disk for installed tools and save results."""
        tools = self._scanner.scan_all()
        self._settings.set_tools(tools)
        return [t.to_dict() for t in tools]

    def get_tools(self) -> list[dict[str, Any]]:
        """Get registered tools from settings."""
        tools = self._settings.get_tools()
        if not tools:
            tools = self._scanner.scan_all()
            self._settings.set_tools(tools)
        return [t.to_dict() for t in tools]

    def save_tool(self, tool_dict: dict[str, Any]) -> dict[str, Any]:
        """Update a tool's config (e.g., exe_path)."""
        try:
            tool = ToolInfo.from_dict(tool_dict)
            self._settings.update_tool(tool)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Tool config (read/write external configs)
    # ------------------------------------------------------------------

    def get_tool_tasks(self, tool_id: str) -> list[dict[str, Any]]:
        """Get available tasks for a tool by reading its config."""
        adapter = _ADAPTERS.get(tool_id, _NULL)
        tool = self._find_tool(tool_id)
        if not tool or not adapter.can_read():
            return []
        try:
            tasks = adapter.read_tasks(tool.install_dir)
            return [t.to_dict() for t in tasks]
        except Exception as e:
            logger.warning("Failed to read tasks for {}: {}", tool_id, e)
            return []

    def get_tool_settings(self, tool_id: str) -> dict[str, Any]:
        """Get tool-specific settings."""
        adapter = _ADAPTERS.get(tool_id, _NULL)
        tool = self._find_tool(tool_id)
        if not tool or not adapter.can_read():
            return {}
        try:
            return adapter.read_settings(tool.install_dir)
        except Exception as e:
            logger.warning("Failed to read settings for {}: {}", tool_id, e)
            return {}

    def save_tool_settings(self, tool_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        """Write modified settings back to a tool's config files."""
        adapter = _ADAPTERS.get(tool_id, _NULL)
        tool = self._find_tool(tool_id)
        if not tool:
            return {"ok": False, "error": f"Tool {tool_id} not found"}
        if not adapter.can_write():
            return {"ok": False, "error": f"Writing not supported for {tool_id}"}
        try:
            adapter.write_settings(tool.install_dir, settings)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Schedules
    # ------------------------------------------------------------------

    def get_schedules(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._settings.get_schedules()]

    def save_schedule(self, schedule_dict: dict[str, Any]) -> dict[str, Any]:
        try:
            sched = Schedule.from_dict(schedule_dict)
            self._settings.save_schedule(sched)
            return {"ok": True, "id": sched.id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_schedule(self, schedule_id: str) -> dict[str, Any]:
        ok = self._settings.delete_schedule(schedule_id)
        return {"ok": ok}

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_plan(self, plan_dict: dict[str, Any]) -> dict[str, Any]:
        """Execute a plan. Non-blocking."""
        if self._run_thread and self._run_thread.is_alive():
            return {"ok": False, "error": "已有任务在运行"}

        try:
            plan = Plan.from_dict(plan_dict)
        except Exception as e:
            return {"ok": False, "error": f"Invalid plan: {e}"}

        tools = {t.tool_id: t for t in self._settings.get_tools()}
        self._executor = DagExecutor(tools)

        def _run() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self._executor.run(plan))
                logger.info("Run complete: success={}", result.success)
                # Run post-action
                loop.run_until_complete(run_post_action(plan.post_action))
            except Exception:
                logger.exception("Plan execution failed")
            finally:
                self._executor = None

        self._run_thread = threading.Thread(target=_run, daemon=True, name="plan-run")
        self._run_thread.start()
        return {"ok": True}

    def stop(self) -> dict[str, Any]:
        """Stop the current run."""
        if self._executor:
            self._executor.cancel()
            return {"ok": True}
        return {"ok": False, "error": "没有正在运行的任务"}

    def get_status(self) -> dict[str, Any]:
        """Get current run status."""
        running = self._run_thread is not None and self._run_thread.is_alive()
        return {"running": running}

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    def start_scheduler(self) -> None:
        self._scheduler.start()

    def stop_scheduler(self) -> None:
        self._scheduler.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_tool(self, tool_id: str) -> ToolInfo | None:
        for t in self._settings.get_tools():
            if t.tool_id == tool_id:
                return t
        return None

    def _on_schedule_fire(self, sched: Schedule) -> None:
        """Called by the scheduler when a cron matches."""
        logger.info("Schedule fired: {}", sched.name)
        self.run_plan(sched.plan.to_dict())
