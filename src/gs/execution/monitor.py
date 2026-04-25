"""Monitor a running tool process for completion."""
from __future__ import annotations

import asyncio
import subprocess

from loguru import logger

from gs.core.models import RunStatus


async def wait_for_exit(
    proc: subprocess.Popen[bytes],
    timeout_s: float,
    poll_interval: float = 3.0,
) -> tuple[RunStatus, int | None, str]:
    """Poll *proc* until it exits or *timeout_s* is reached.

    Returns ``(status, exit_code, last_output_lines)``.
    """
    elapsed = 0.0
    output_lines: list[str] = []

    while elapsed < timeout_s:
        rc = proc.poll()
        if rc is not None:
            # Process exited
            _drain_output(proc, output_lines)
            status = RunStatus.SUCCESS if rc == 0 else RunStatus.FAILED
            logger.info("Process exited: code={} status={}", rc, status.value)
            return status, rc, "\n".join(output_lines[-30:])

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        _drain_output(proc, output_lines)

    # Timeout — kill the process
    logger.warning("Process timed out after {}s, killing", timeout_s)
    _kill(proc)
    return RunStatus.TIMEOUT, None, "\n".join(output_lines[-30:])


def kill_process(proc: subprocess.Popen[bytes]) -> None:
    """Graceful then forceful kill."""
    _kill(proc)


def _kill(proc: subprocess.Popen[bytes]) -> None:
    """Terminate then kill with grace period."""
    try:
        proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass


def _drain_output(proc: subprocess.Popen[bytes], lines: list[str]) -> None:
    """Non-blocking read of available stdout."""
    if proc.stdout is None:
        return
    while True:
        try:
            # Non-blocking: read whatever is available
            data = proc.stdout.read1(4096)  # type: ignore[attr-defined]
            if not data:
                break
            for line in data.decode("utf-8", errors="replace").splitlines():
                lines.append(line)
                if len(lines) > 200:
                    lines.pop(0)
        except (BlockingIOError, AttributeError):
            break
