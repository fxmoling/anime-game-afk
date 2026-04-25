"""Adapter for aether-gazer-afk (深空之眼 automation tool)."""
from __future__ import annotations

from game_scheduler.models import ToolConfig, ToolRun

from .base import BaseAdapter


class AetherGazerAdapter(BaseAdapter):
    """aether-gazer-afk adapter (深空之眼)."""

    _tool_id: str = "aether"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        cmd = [tool_config.exe_path]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)
        else:
            cmd.append("--daily")

        cmd.extend(tool_run.extra_args)
        return cmd
