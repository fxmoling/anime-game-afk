"""Preflight health checks for tools."""
from __future__ import annotations

from pathlib import Path

from gs.core.models import ToolInfo, ToolStatus


def check_health(tool: ToolInfo) -> tuple[bool, str]:
    """Verify a tool is ready to run.

    Returns ``(ok, message)``.
    """
    if tool.status == ToolStatus.NOT_FOUND:
        return False, f"{tool.name} 未找到"

    if not tool.exe_path:
        return False, f"{tool.name} 未配置路径"

    exe = Path(tool.exe_path)
    if not exe.is_file():
        return False, f"可执行文件不存在: {exe}"

    return True, "就绪"
