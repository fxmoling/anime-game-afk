"""Generic adapter for arbitrary executables."""
from __future__ import annotations

from game_scheduler.models import ToolConfig, ToolRun

from .base import BaseAdapter


class GenericAdapter(BaseAdapter):
    """Passthrough adapter for any executable."""

    _tool_id: str = "generic"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        return [tool_config.exe_path, *tool_config.args_template, *tool_run.extra_args]
