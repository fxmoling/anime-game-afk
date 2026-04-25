"""BetterGI config adapter — Level 1 (read-only).

Reads BetterGI's OneDragon configs and script groups.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from gs.config.base import TaskOption

BETTERGI_DEFAULT_TASKS = [
    ("GetMail", "领取邮件"),
    ("SynthesizeResin", "合成树脂"),
    ("AutoDomain", "自动秘境"),
    ("AutoAbyss", "自动幽境危战"),
    ("AutoLeyLines", "自动地脉花"),
    ("GetDailyRewards", "领取每日奖励"),
    ("GetTeapotRewards", "领取尘歌壶奖励"),
]


class BettergiConfigAdapter:
    """Read BetterGI's configuration."""

    tool_id = "bettergi"

    def can_read(self) -> bool:
        return True

    def can_write(self) -> bool:
        return False

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        """Read OneDragon configs or return defaults."""
        od_dir = Path(install_dir) / "User" / "OneDragon"
        if od_dir.is_dir():
            configs = [f.stem for f in od_dir.glob("*.json")]
            if configs:
                return [TaskOption(id=c, name=f"一条龙: {c}") for c in configs]

        return [TaskOption(id=tid, name=name) for tid, name in BETTERGI_DEFAULT_TASKS]

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        config_path = Path(install_dir) / "User" / "config.json"
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to read BetterGI config")
            return {}

    def write_settings(self, install_dir: str, settings: dict[str, Any]) -> None:
        raise NotImplementedError("BetterGI config writing not yet supported")
