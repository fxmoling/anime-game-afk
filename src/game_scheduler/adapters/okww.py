"""Adapter for ok-ww (鸣潮 — Wuthering Waves assistant)."""
from __future__ import annotations

from game_scheduler.models import ToolConfig, ToolRun

from .base import BaseAdapter


class OkwwAdapter(BaseAdapter):
    """ok-ww adapter (鸣潮 - Wuthering Waves)."""

    _tool_id: str = "okww"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        task_index = tool_run.task_index if tool_run.task_index is not None else 1

        cmd = [
            tool_config.exe_path,
            "-t", str(task_index),
            "-e",
        ]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)

        cmd.extend(tool_run.extra_args)
        return cmd
