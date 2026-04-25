"""Adapter for M9A (1999 助手)."""
from __future__ import annotations

from game_scheduler.models import ToolConfig, ToolRun

from .base import BaseAdapter


class M9aAdapter(BaseAdapter):
    """M9A adapter (重返未来：1999)."""

    _tool_id: str = "m9a"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        cmd = [tool_config.exe_path, "-d"]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)

        cmd.extend(tool_run.extra_args)
        return cmd
