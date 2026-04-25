"""MAA config adapter — Level 2 (read + write).

Reads MAA's ``config/gui.json`` and ``config/gui.new.json`` to discover
available tasks and their settings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from gs.config.base import ConfigAdapter, TaskOption

# MAA task types in execution order
MAA_TASKS = [
    ("StartUp", "开始唤醒"),
    ("Fight", "刷理智"),
    ("Recruit", "自动公招"),
    ("Infrast", "基建换班"),
    ("Mall", "领取信用及购物"),
    ("Award", "领取日常奖励"),
    ("Roguelike", "自动肉鸽"),
    ("Reclamation", "生息演算"),
    ("CloseDown", "关闭游戏"),
]


class MaaConfigAdapter:
    """Read/write MAA gui.json config."""

    tool_id = "maa"

    def can_read(self) -> bool:
        return True

    def can_write(self) -> bool:
        return True

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        """Read MAA's task queue from gui.new.json."""
        gui_new = self._load_gui_new(install_dir)
        if not gui_new:
            # Fallback: return default task list
            return [TaskOption(id=tid, name=name) for tid, name in MAA_TASKS]

        # Parse task queue from Default configuration
        configs = gui_new.get("Configurations", {})
        default = configs.get("Default", configs.get(gui_new.get("Current", ""), {}))
        queue = default.get("TaskQueue", [])

        tasks = []
        for item in queue:
            task_type = item.get("TaskType", "")
            is_enabled = item.get("IsEnable", False)
            zh_name = dict(MAA_TASKS).get(task_type, task_type)
            tasks.append(TaskOption(
                id=task_type,
                name=zh_name,
                enabled=is_enabled,
            ))

        # Ensure all known tasks are present
        seen = {t.id for t in tasks}
        for tid, name in MAA_TASKS:
            if tid not in seen:
                tasks.append(TaskOption(id=tid, name=name, enabled=False))

        return tasks

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        """Read MAA global + default config settings."""
        gui = self._load_gui(install_dir)
        if not gui:
            return {}

        result: dict[str, Any] = {}

        # Global settings
        g = gui.get("Global", {})
        result["client_type"] = g.get("Start.ClientType", "Official")

        # Default configuration
        configs = gui.get("Configurations", {})
        current = gui.get("Current", "Default")
        default = configs.get(current, configs.get("Default", {}))

        result["connect_address"] = default.get("Connect.Address", "")
        result["start_game"] = default.get("Start.StartGame", "True") == "True"
        result["post_actions"] = default.get("MainFunction.PostActions", "")

        return result

    def write_settings(self, install_dir: str, settings: dict[str, Any]) -> None:
        """Write settings back to MAA gui.json."""
        gui_path = Path(install_dir) / "config" / "gui.json"
        if not gui_path.exists():
            logger.warning("MAA gui.json not found at {}", gui_path)
            return

        gui = json.loads(gui_path.read_text(encoding="utf-8"))

        g = gui.setdefault("Global", {})
        configs = gui.setdefault("Configurations", {})
        current = gui.get("Current", "Default")
        default = configs.setdefault(current, {})

        # Apply settings
        if "client_type" in settings:
            default["Start.ClientType"] = settings["client_type"]
        if "connect_address" in settings:
            default["Connect.Address"] = settings["connect_address"]
        if "start_game" in settings:
            default["Start.StartGame"] = "True" if settings["start_game"] else "False"

        # Write back
        gui_path.write_text(
            json.dumps(gui, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("MAA settings written to {}", gui_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_gui(install_dir: str) -> dict[str, Any] | None:
        path = Path(install_dir) / "config" / "gui.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to parse {}", path)
            return None

    @staticmethod
    def _load_gui_new(install_dir: str) -> dict[str, Any] | None:
        path = Path(install_dir) / "config" / "gui.new.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to parse {}", path)
            return None
