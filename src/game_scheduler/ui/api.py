"""Standalone API for the game scheduler — exposed to pywebview frontend."""
from __future__ import annotations

from typing import Any

from loguru import logger

from game_scheduler.run_manager import OrchestratorRunManager


class SchedulerApi:
    """API methods exposed to the Vue frontend via pywebview."""

    def __init__(self, manager: OrchestratorRunManager) -> None:
        self._mgr = manager

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def orch_get_tools(self) -> list[dict[str, Any]]:
        return self._mgr.get_tools()

    def orch_save_tool(self, tool_dict: dict[str, Any]) -> dict[str, Any]:
        return self._mgr.save_tool(tool_dict)

    def orch_remove_tool(self, tool_id: str) -> dict[str, Any]:
        return self._mgr.remove_tool(tool_id)

    def orch_scan_tools(self) -> list[dict[str, Any]]:
        return self._mgr.scan_tools()

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def orch_get_schedules(self) -> list[dict[str, Any]]:
        return self._mgr.get_schedules()

    def orch_save_schedule(self, schedule_dict: dict[str, Any]) -> dict[str, Any]:
        return self._mgr.save_schedule(schedule_dict)

    def orch_remove_schedule(self, schedule_id: str) -> dict[str, Any]:
        return self._mgr.remove_schedule(schedule_id)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def orch_run_now(self, schedule_id: str) -> dict[str, Any]:
        return self._mgr.run_now(schedule_id)

    def orch_run_plan(self, plan_dict: dict[str, Any]) -> dict[str, Any]:
        return self._mgr.run_plan(plan_dict)

    def orch_stop(self) -> dict[str, Any]:
        return self._mgr.stop()

    def orch_get_run_status(self) -> dict[str, Any]:
        return self._mgr.get_run_status()

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def get_recent_logs(self, count: int = 200) -> list[str]:
        """Return recent log lines from loguru sink."""
        return list(_log_buffer)[-count:]


# ---------------------------------------------------------------------------
# In-memory log buffer for the UI
# ---------------------------------------------------------------------------

from collections import deque

_log_buffer: deque[str] = deque(maxlen=2000)


def _log_sink(message: Any) -> None:
    _log_buffer.append(str(message).rstrip())


def setup_log_sink() -> None:
    """Add a loguru sink that captures logs for the UI."""
    logger.add(_log_sink, format="{time:HH:mm:ss} | {level:<7} | {message}", level="DEBUG")
