"""Application settings — YAML-backed, crash-safe."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from gs.core.models import Schedule, ToolInfo

_DEFAULT_PATH = Path("config/settings.yaml")


class Settings:
    """YAML-backed app settings with typed accessors.

    Manages tool registry and schedule entries.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_PATH
        self._data: dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    self._data = yaml.safe_load(f) or {}
                logger.debug("Settings loaded from {}", self._path)
            except Exception:
                logger.exception("Failed to load settings, using defaults")
                self._data = {}
        else:
            logger.info("No settings file, starting fresh")

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)
        tmp.replace(self._path)
        logger.debug("Settings saved to {}", self._path)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def get_tools(self) -> list[ToolInfo]:
        raw = self._data.get("tools", [])
        return [ToolInfo.from_dict(d) for d in raw]

    def set_tools(self, tools: list[ToolInfo]) -> None:
        self._data["tools"] = [t.to_dict() for t in tools]
        self.save()

    def update_tool(self, tool: ToolInfo) -> None:
        tools = self.get_tools()
        for i, t in enumerate(tools):
            if t.tool_id == tool.tool_id:
                tools[i] = tool
                self.set_tools(tools)
                return
        tools.append(tool)
        self.set_tools(tools)

    # ------------------------------------------------------------------
    # Schedules
    # ------------------------------------------------------------------

    def get_schedules(self) -> list[Schedule]:
        raw = self._data.get("schedules", [])
        return [Schedule.from_dict(d) for d in raw]

    def set_schedules(self, schedules: list[Schedule]) -> None:
        self._data["schedules"] = [s.to_dict() for s in schedules]
        self.save()

    def save_schedule(self, schedule: Schedule) -> None:
        schedules = self.get_schedules()
        for i, s in enumerate(schedules):
            if s.id == schedule.id:
                schedules[i] = schedule
                self.set_schedules(schedules)
                return
        schedules.append(schedule)
        self.set_schedules(schedules)

    def delete_schedule(self, schedule_id: str) -> bool:
        schedules = self.get_schedules()
        before = len(schedules)
        schedules = [s for s in schedules if s.id != schedule_id]
        if len(schedules) < before:
            self.set_schedules(schedules)
            return True
        return False

    # ------------------------------------------------------------------
    # Generic access
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()
