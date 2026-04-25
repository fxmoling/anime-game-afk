"""Adapter for MAA (MaaAssistantArknights) CLI."""
from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

from game_scheduler.models import ToolConfig, ToolRun

from .base import BaseAdapter


class MaaAdapter(BaseAdapter):
    """MAA CLI adapter (明日方舟 - Arknights)."""

    _tool_id: str = "maa"

    async def preflight(self, tool_config: ToolConfig) -> tuple[bool, str]:
        ok, msg = await super().preflight(tool_config)
        if not ok:
            return ok, msg

        exe = Path(tool_config.exe_path)
        exe_name = exe.stem.lower()
        if exe_name == "maa" or exe_name == "maa_cli":
            return True, ""

        if shutil.which("maa") is None:
            parent_dir = exe.parent
            maa_candidates = list(parent_dir.glob("maa.exe")) + list(
                parent_dir.glob("maa")
            )
            if not maa_candidates:
                return False, "maa CLI 不在 PATH 中, 也不在工具目录下"
            logger.debug("maa CLI 找到: {}", maa_candidates[0])
        return True, ""

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        exe = tool_config.exe_path

        if tool_config.args_template:
            return [exe, *tool_config.args_template, *tool_run.extra_args]

        if tool_run.extra_args:
            return [exe, *tool_run.extra_args]

        config = tool_run.config_name or "daily"
        return [exe, "run", config]
