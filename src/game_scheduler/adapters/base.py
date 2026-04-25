"""Base protocol and shared logic for tool adapters."""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

from loguru import logger

from game_scheduler.models import (
    CompletionStrategy,
    ToolConfig,
    ToolRun,
    ToolRunStatus,
)

_STOP_GRACE_SECONDS: int = 5


@runtime_checkable
class ToolAdapter(Protocol):
    """Interface that every tool adapter must satisfy."""

    @property
    def tool_id(self) -> str: ...

    async def preflight(self, tool_config: ToolConfig) -> tuple[bool, str]: ...

    async def start(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> subprocess.Popen[bytes]: ...

    async def poll(self, process: subprocess.Popen[bytes]) -> ToolRunStatus: ...

    async def stop(self, process: subprocess.Popen[bytes]) -> None: ...

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]: ...


class BaseAdapter:
    """Shared implementation for :class:`ToolAdapter`."""

    _tool_id: str = ""

    @property
    def tool_id(self) -> str:
        return self._tool_id

    async def preflight(self, tool_config: ToolConfig) -> tuple[bool, str]:
        exe = Path(tool_config.exe_path)
        if not exe.exists():
            return False, f"可执行文件不存在: {exe}"
        if not exe.is_file():
            return False, f"路径不是文件: {exe}"
        return True, ""

    async def start(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> subprocess.Popen[bytes]:
        cmd = self.build_command(tool_config, tool_run)
        cwd = tool_config.working_dir or str(Path(tool_config.exe_path).parent)

        logger.info("[{}] 启动命令: {}", self.tool_id, " ".join(cmd))

        creation_flags: int = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        logger.info("[{}] 进程已启动, PID={}", self.tool_id, process.pid)
        return process

    async def poll(self, process: subprocess.Popen[bytes]) -> ToolRunStatus:
        rc = process.poll()
        if rc is None:
            return ToolRunStatus.RUNNING
        return ToolRunStatus.SUCCESS if rc == 0 else ToolRunStatus.FAILED

    async def stop(self, process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return

        logger.info("[{}] 终止进程 PID={}", self.tool_id, process.pid)
        try:
            process.terminate()
        except OSError:
            return

        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, process.wait,
                ),
                timeout=_STOP_GRACE_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("[{}] 进程未响应, 强制结束 PID={}", self.tool_id, process.pid)
            try:
                process.kill()
                process.wait(timeout=3)
            except OSError:
                pass

    def build_command(
        self,
        tool_config: ToolConfig,
        tool_run: ToolRun,
    ) -> list[str]:
        return [tool_config.exe_path, *tool_config.args_template, *tool_run.extra_args]
