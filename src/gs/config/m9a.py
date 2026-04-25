"""M9A config adapter — Level 1 (read-only).

Reads M9A's interface.json for available tasks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from gs.config.base import TaskOption


class M9aConfigAdapter:
    """Read M9A task definitions from interface.json."""

    tool_id = "m9a"

    def can_read(self) -> bool:
        return True

    def can_write(self) -> bool:
        return False

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        """Read tasks from interface.json imports."""
        interface = self._load_interface(install_dir)
        if not interface:
            return []

        tasks = []
        for task_def in interface.get("task", []):
            tasks.append(TaskOption(
                id=task_def.get("entry", task_def.get("name", "")),
                name=task_def.get("name", ""),
            ))
        return tasks

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        interface = self._load_interface(install_dir)
        if not interface:
            return {}
        return {
            "name": interface.get("name", "M9A"),
            "version": interface.get("version", ""),
        }

    def write_settings(self, install_dir: str, settings: dict[str, Any]) -> None:
        raise NotImplementedError("M9A config writing not yet supported")

    @staticmethod
    def _load_interface(install_dir: str) -> dict[str, Any] | None:
        for name in ["interface.json", "assets/interface.json"]:
            path = Path(install_dir) / name
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    logger.warning("Failed to parse {}", path)
        return None
