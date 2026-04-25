"""Adapter for BetterGI (原神 — Genshin Impact helper)."""
from __future__ import annotations

import asyncio
import subprocess
import sys

from loguru import logger

from game_scheduler.models import ToolConfig, ToolRun, ToolRunStatus

from .base import BaseAdapter, _STOP_GRACE_SECONDS


class BetterGiAdapter(BaseAdapter):
    """BetterGI adapter (原神 - Genshin Impact)."""

    _tool_id: str = "bettergi"

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        config = tool_run.config_name or "默认"

        cmd = [tool_config.exe_path, "startOneDragon", config]

        if tool_config.args_template:
            cmd.extend(tool_config.args_template)

        cmd.extend(tool_run.extra_args)
        return cmd

    async def poll(self, process: subprocess.Popen[bytes]) -> ToolRunStatus:
        rc = process.poll()
        if rc is None:
            return ToolRunStatus.RUNNING
        return ToolRunStatus.SUCCESS if rc == 0 else ToolRunStatus.FAILED

    async def stop(self, process: subprocess.Popen[bytes]) -> None:
        await super().stop(process)
        await self._kill_game_processes()

    @staticmethod
    async def _kill_game_processes(
        names: list[str] | None = None,
    ) -> None:
        targets = names or ["YuanShen.exe", "GenshinImpact.exe", "Genshin Impact"]
        if sys.platform != "win32":
            return

        for name in targets:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "taskkill", "/F", "/IM", name,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                await proc.wait()
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.debug("结束 {} 失败: {}", name, exc)
