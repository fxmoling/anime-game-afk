"""Build CLI commands and launch tool subprocesses."""
from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger

from gs.core.models import ToolInfo, TaskConfig
from gs.discovery.registry import TOOLS


def build_command(tool: ToolInfo, task: TaskConfig) -> list[str]:
    """Build the CLI argument list for a tool run.

    Uses the template from ``registry.TOOLS`` and substitutes placeholders.
    Extra ``task.cli_args`` are appended.
    """
    sig = TOOLS.get(tool.tool_id)
    if sig is None or not sig.cli_template:
        return [tool.exe_path] + task.cli_args

    cmd: list[str] = []
    for part in sig.cli_template:
        if part == "{exe}":
            cmd.append(tool.exe_path)
        elif part == "{config_name}":
            name = (task.config_overrides or {}).get("config_name", "")
            if name:
                cmd.append(name)
        elif part == "{task_index}":
            idx = (task.config_overrides or {}).get("task_index", "1")
            cmd.append(str(idx))
        else:
            cmd.append(part)

    cmd.extend(task.cli_args)
    return cmd


def start_process(cmd: list[str], cwd: str | None = None) -> subprocess.Popen[bytes]:
    """Launch a subprocess with proper Windows flags.

    Returns the ``Popen`` handle for monitoring.
    """
    work_dir = cwd or str(Path(cmd[0]).parent)
    logger.info("Starting: {} (cwd={})", " ".join(cmd), work_dir)

    return subprocess.Popen(
        cmd,
        cwd=work_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
