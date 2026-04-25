"""DAG executor: run a Plan as sequential waves of parallel tasks."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger

from gs.core.models import (
    Plan, RunResult, RunStatus, TaskConfig, TaskResult, ToolInfo, WaveResult,
)
from gs.discovery.health import check_health
from gs.execution.launcher import build_command, start_process
from gs.execution.monitor import kill_process, wait_for_exit


class DagExecutor:
    """Execute a Plan: sequential waves, parallel tasks within each wave.

    Usage::

        executor = DagExecutor(tools)
        result = await executor.run(plan)
    """

    def __init__(self, tools: dict[str, ToolInfo]) -> None:
        self._tools = tools
        self._cancelled = False
        self._running_procs: list = []

    async def run(self, plan: Plan) -> RunResult:
        """Execute *plan* and return the result."""
        result = RunResult(plan_name=plan.name, started_at=datetime.now(timezone.utc))
        self._cancelled = False

        logger.info("Starting plan: {} ({} waves)", plan.name, len(plan.waves))

        for wave_idx, wave in enumerate(plan.waves):
            if self._cancelled:
                result.aborted = True
                break

            logger.info("Wave {}: {} tasks", wave_idx, len(wave.tasks))
            wave_result = WaveResult(index=wave_idx)

            task_results = await asyncio.gather(
                *[self._run_task(t) for t in wave.tasks],
                return_exceptions=True,
            )

            for tr in task_results:
                if isinstance(tr, Exception):
                    logger.error("Task exception: {}", tr)
                    wave_result.tasks.append(
                        TaskResult(tool_id="?", status=RunStatus.FAILED, error=str(tr))
                    )
                else:
                    wave_result.tasks.append(tr)

            result.waves.append(wave_result)

        result.finished_at = datetime.now(timezone.utc)
        logger.info("Plan finished: success={}", result.success)
        return result

    async def _run_task(self, task: TaskConfig) -> TaskResult:
        """Run a single tool task."""
        tr = TaskResult(tool_id=task.tool_id)

        tool = self._tools.get(task.tool_id)
        if tool is None:
            tr.status = RunStatus.FAILED
            tr.error = f"Tool {task.tool_id!r} not registered"
            return tr

        ok, msg = check_health(tool)
        if not ok:
            tr.status = RunStatus.SKIPPED
            tr.error = msg
            logger.warning("Preflight failed for {}: {}", task.tool_id, msg)
            return tr

        cmd = build_command(tool, task)
        tr.started_at = datetime.now(timezone.utc)

        try:
            proc = start_process(cmd, cwd=tool.install_dir or None)
            self._running_procs.append(proc)

            status, exit_code, output = await wait_for_exit(
                proc, timeout_s=task.timeout_min * 60,
            )

            tr.status = status
            tr.exit_code = exit_code
            if status == RunStatus.FAILED:
                tr.error = f"Exit code {exit_code}"
        except Exception as e:
            tr.status = RunStatus.FAILED
            tr.error = str(e)
            logger.exception("Failed to run {}", task.tool_id)
        finally:
            tr.finished_at = datetime.now(timezone.utc)
            if proc in self._running_procs:
                self._running_procs.remove(proc)

        return tr

    def cancel(self) -> None:
        """Cancel the current run and kill all running processes."""
        self._cancelled = True
        for proc in self._running_procs:
            kill_process(proc)
        self._running_procs.clear()
