"""ZZZ-OneDragon config adapter — Level 1 (read-only)."""
from __future__ import annotations

from typing import Any

from gs.config.base import TaskOption

ZZZ_APPS = [
    ("coffee", "咖啡店"),
    ("charge_plan", "体力计划"),
    ("world_patrol", "世界巡防"),
    ("hollow_zero_lost_void", "空洞-迷失之地"),
    ("shiyu_defense", "希兹防线"),
    ("email_app", "邮件"),
    ("city_fund", "城市资金"),
    ("notorious_hunt", "恶名狩猎"),
    ("redemption_code", "兑换码"),
]


class ZzzConfigAdapter:
    """Read ZZZ-OneDragon's available applications."""

    tool_id = "zzz"

    def can_read(self) -> bool:
        return True

    def can_write(self) -> bool:
        return False

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        return [TaskOption(id=aid, name=name) for aid, name in ZZZ_APPS]

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        return {"app_count": len(ZZZ_APPS)}

    def write_settings(self, install_dir: str, settings: dict[str, Any]) -> None:
        raise NotImplementedError("ZZZ config writing not yet supported")
