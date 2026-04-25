"""ok-ww config adapter — Level 1 (read-only for now).

Reads ok-ww's task list from config.py structure.
"""
from __future__ import annotations

from typing import Any

from gs.config.base import TaskOption

# ok-ww tasks in order (from config.py onetime_tasks)
OKWW_TASKS = [
    ("1", "DailyTask", "日常一条龙"),
    ("2", "MultiAccountDailyTask", "多账号一条龙"),
    ("3", "FarmEchoTask", "刷声骸"),
    ("4", "AutoRogueTask", "自动肉鸽"),
    ("5", "ForgeryTask", "锻造挑战"),
    ("6", "NightmareNestTask", "噩梦巢穴"),
    ("7", "SimulationTask", "模拟挑战"),
    ("8", "TacetTask", "无声区"),
    ("9", "EnhanceEchoTask", "声骸强化"),
    ("10", "ChangeEchoTask", "换声骸"),
    ("11", "DiagnosisTask", "诊断"),
]


class OkwwConfigAdapter:
    """Read ok-ww's available tasks."""

    tool_id = "okww"

    def can_read(self) -> bool:
        return True

    def can_write(self) -> bool:
        return False  # Future: write ok-ww configs

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        return [
            TaskOption(id=idx, name=name, description=class_name)
            for idx, class_name, name in OKWW_TASKS
        ]

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        return {"task_count": len(OKWW_TASKS)}

    def write_settings(self, install_dir: str, settings: dict[str, Any]) -> None:
        raise NotImplementedError("ok-ww config writing not yet supported")
