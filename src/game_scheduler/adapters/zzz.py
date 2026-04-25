"""Adapter for ZZZ-OneDragon (绝区零 — Zenless Zone Zero assistant)."""
from __future__ import annotations

from game_scheduler.models import ToolConfig, ToolRun

from .base import BaseAdapter


class ZzzAdapter(BaseAdapter):
    """ZZZ-OneDragon adapter (绝区零)."""

    _tool_id: str = "zzz"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        cmd = [tool_config.exe_path, "-o"]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)

        cmd.extend(tool_run.extra_args)
        return cmd
