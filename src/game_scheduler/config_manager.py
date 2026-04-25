"""Manages orchestrator config stored in a YAML file.

Provides CRUD operations for tool registrations and schedule entries.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from game_scheduler.models import (
    CompletionStrategy,
    ScheduleEntry,
    ToolConfig,
    ToolType,
)


# ---------------------------------------------------------------------------
# Default tool presets
# ---------------------------------------------------------------------------

_DEFAULT_TOOLS: list[dict[str, Any]] = [
    {
        "tool_id": "maa",
        "display_name": "MAA (明日方舟)",
        "exe_path": "",
        "tool_type": "cli",
        "args_template": [],
        "completion": "process_exit",
        "timeout_minutes": 60,
        "icon": "🏰",
        "game_process_names": ["明日方舟.exe", "Arknights.exe"],
    },
    {
        "tool_id": "m9a",
        "display_name": "M9A (1999)",
        "exe_path": "",
        "tool_type": "replay",
        "args_template": ["-d"],
        "completion": "process_exit",
        "timeout_minutes": 45,
        "icon": "🎭",
        "game_process_names": ["Reverse1999.exe"],
    },
    {
        "tool_id": "okww",
        "display_name": "ok-ww (鸣潮)",
        "exe_path": "",
        "tool_type": "cli",
        "args_template": [],
        "completion": "process_exit",
        "timeout_minutes": 45,
        "icon": "🌊",
        "game_process_names": ["Wuthering Waves.exe", "Client-Win64-Shipping.exe"],
    },
    {
        "tool_id": "bettergi",
        "display_name": "BetterGI (原神)",
        "exe_path": "",
        "tool_type": "gui_cli",
        "args_template": [],
        "completion": "process_exit",
        "timeout_minutes": 60,
        "icon": "⚡",
        "game_process_names": ["YuanShen.exe", "GenshinImpact.exe"],
    },
    {
        "tool_id": "zzz",
        "display_name": "ZZZ (绝区零)",
        "exe_path": "",
        "tool_type": "headless",
        "args_template": ["-o"],
        "completion": "process_exit",
        "timeout_minutes": 45,
        "icon": "🎵",
        "game_process_names": ["ZenlessZoneZero.exe"],
    },
    {
        "tool_id": "aether",
        "display_name": "aether-gazer-afk (深空之眼)",
        "exe_path": "",
        "tool_type": "cli",
        "args_template": ["--daily"],
        "completion": "process_exit",
        "timeout_minutes": 30,
        "icon": "👁",
        "game_process_names": ["深空之眼.exe", "AetherGazer.exe"],
    },
]

_DEFAULT_CONFIG_PATH = Path("data/config.yaml")


# ---------------------------------------------------------------------------
# OrchestratorConfigManager
# ---------------------------------------------------------------------------

class OrchestratorConfigManager:
    """Manages tool registry and schedule entries in a YAML config file.

    All reads reload from disk to stay in sync with external edits.
    All writes flush immediately.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}

    def _load(self) -> dict[str, Any]:
        """(Re)load config from disk."""
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    self._data = yaml.safe_load(f) or {}
            except Exception as exc:
                logger.warning("Failed to load config {}: {}", self._path, exc)
                self._data = {}
        else:
            self._data = {}
        return self._data

    def _orch_section(self) -> dict[str, Any]:
        """Get or create the ``orchestrator`` section in config."""
        self._load()
        return self._data.setdefault("orchestrator", {})

    def _save(self) -> None:
        """Persist current config to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def get_tools(self) -> list[ToolConfig]:
        """Return all registered tools."""
        orch = self._orch_section()
        raw_tools: list[dict[str, Any]] = orch.get("tools", [])
        tools: list[ToolConfig] = []
        for d in raw_tools:
            try:
                tools.append(ToolConfig.from_dict(d))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping invalid tool config: {} — {}", d, exc)
        return tools

    def save_tool(self, tool: ToolConfig) -> None:
        """Add or update a tool in the registry."""
        orch = self._orch_section()
        raw_tools: list[dict[str, Any]] = orch.setdefault("tools", [])

        replaced = False
        for i, d in enumerate(raw_tools):
            if d.get("tool_id") == tool.tool_id:
                raw_tools[i] = tool.to_dict()
                replaced = True
                break
        if not replaced:
            raw_tools.append(tool.to_dict())

        self._save()
        logger.info("Saved tool: {}", tool.tool_id)

    def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool by ID. Returns True if found and removed."""
        orch = self._orch_section()
        raw_tools: list[dict[str, Any]] = orch.get("tools", [])
        original_len = len(raw_tools)
        orch["tools"] = [d for d in raw_tools if d.get("tool_id") != tool_id]

        if len(orch["tools"]) < original_len:
            self._save()
            logger.info("Removed tool: {}", tool_id)
            return True
        return False

    def get_default_tools(self) -> list[ToolConfig]:
        """Return preset tool configs for common tools."""
        return [ToolConfig.from_dict(d) for d in _DEFAULT_TOOLS]

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def get_schedules(self) -> list[ScheduleEntry]:
        """Return all schedule entries."""
        orch = self._orch_section()
        raw_schedules: list[dict[str, Any]] = orch.get("schedules", [])
        entries: list[ScheduleEntry] = []
        for d in raw_schedules:
            try:
                entries.append(ScheduleEntry.from_dict(d))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping invalid schedule config: {} — {}", d, exc)
        return entries

    def save_schedule(self, entry: ScheduleEntry | Any) -> None:
        """Add or update a schedule entry."""
        if isinstance(entry, ScheduleEntry):
            entry_dict = entry.to_dict()
            schedule_id = entry.schedule_id
        else:
            entry_dict = entry
            schedule_id = entry.get("schedule_id", "")

        orch = self._orch_section()
        raw_schedules: list[dict[str, Any]] = orch.setdefault("schedules", [])

        replaced = False
        for i, d in enumerate(raw_schedules):
            if d.get("schedule_id") == schedule_id:
                raw_schedules[i] = entry_dict
                replaced = True
                break
        if not replaced:
            raw_schedules.append(entry_dict)

        self._save()
        logger.info("Saved schedule: {} ({})", schedule_id, entry_dict.get("name", ""))

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule by ID. Returns True if found and removed."""
        orch = self._orch_section()
        raw_schedules: list[dict[str, Any]] = orch.get("schedules", [])
        original_len = len(raw_schedules)
        orch["schedules"] = [
            d for d in raw_schedules if d.get("schedule_id") != schedule_id
        ]

        if len(orch["schedules"]) < original_len:
            self._save()
            logger.info("Removed schedule: {}", schedule_id)
            return True
        return False
