"""DAG executor — runs a RunPlan as sequential waves of parallel tool runs.

Each wave runs all its tools concurrently via ``asyncio.gather()``.
Waves run sequentially — wave *N+1* starts only after wave *N* completes.
State is persisted after each wave for crash recovery.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from loguru import logger

from game_scheduler.models import (
    PostAction,
    RunPlan,
    RunResult,
    ToolConfig,
    ToolResult,
    ToolRun,
    ToolRunStatus,
    Wave,
    WaveResult,
    WaveStatus,
)
from game_scheduler.post_actions import execute_post_action
from game_scheduler.runtime.events import EventBus
from game_scheduler.runtime.state import StateStore

# ---------------------------------------------------------------------------
# Event name constants
# ---------------------------------------------------------------------------

ORCHESTRATOR_RUN_STARTED = "orchestrator_run_started"
ORCHESTRATOR_WAVE_STARTED = "orchestrator_wave_started"
ORCHESTRATOR_TOOL_STARTED = "orchestrator_tool_started"
ORCHESTRATOR_TOOL_COMPLETED = "orchestrator_tool_completed"
ORCHESTRATOR_WAVE_COMPLETED = "orchestrator_wave_completed"
ORCHESTRATOR_RUN_COMPLETED = "orchestrator_run_completed"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_POLL_INTERVAL_SECONDS = 3
_LOG_TAIL_LINES = 50
_STATE_KEY = "orchestrator_run"


# ---------------------------------------------------------------------------
# Adapter protocol (implemented by tool-specific adapters)
# ---------------------------------------------------------------------------

@runtime_checkable
class BaseAdapter(Protocol):
    """Minimal interface every tool adapter must satisfy."""

    async def preflight(self, config: ToolConfig, tool_run: ToolRun) -> str | None:
        """Check prerequisites. Return *None* on success or an error message."""
        ...

    async def start(
        self,
        config: ToolConfig,
        tool_run: ToolRun,
    ) -> asyncio.subprocess.Process:
        """Launch the tool process and return the ``asyncio.subprocess.Process``."""
        ...

    async def stop(self, process: asyncio.subprocess.Process) -> None:
        """Forcefully stop a running process."""
        ...


# ---------------------------------------------------------------------------
# DAG Executor
# ---------------------------------------------------------------------------

class DagExecutor:
    """Executes a :class:`RunPlan` as sequential waves of parallel tool runs."""

    def __init__(
        self,
        tool_registry: dict[str, ToolConfig],
        adapters: dict[str, BaseAdapter],
        state: StateStore,
        bus: EventBus,
    ) -> None:
        self._registry = tool_registry
        self._adapters = adapters
        self._state = state
        self._bus = bus
        self._cancelled = False
        self._running_processes: list[asyncio.subprocess.Process] = []

    async def execute(
        self,
        plan: RunPlan,
        resume_from_wave: int = 0,
    ) -> RunResult:
        """Execute *plan*, optionally resuming from a specific wave."""
        self._cancelled = False
        run_id = uuid.uuid4().hex[:8]
        started_at = datetime.now(timezone.utc)

        result = RunResult(
            run_id=run_id,
            plan_name=plan.name,
            started_at=started_at,
        )

        self._persist_run_state(result, current_wave=resume_from_wave)
        self._bus.emit(
            ORCHESTRATOR_RUN_STARTED,
            run_id=run_id,
            plan_name=plan.name,
            total_waves=len(plan.waves),
        )
        logger.info(
            "Run {} started — plan={!r}, waves={}, resume_from={}",
            run_id, plan.name, len(plan.waves), resume_from_wave,
        )

        abort = False
        abort_reason = ""

        for wave_idx in range(resume_from_wave, len(plan.waves)):
            if self._cancelled:
                abort = True
                abort_reason = "Cancelled by user"
                logger.warning("Run {} cancelled before wave {}", run_id, wave_idx)
                break

            wave = plan.waves[wave_idx]
            wave_result = await self._execute_wave(wave, wave_idx, run_id)
            result.wave_results.append(wave_result)

            self._persist_run_state(result, current_wave=wave_idx + 1)

            if wave_result.status == WaveStatus.ABORTED:
                abort = True
                failed_tools = [
                    tr.tool_id
                    for tr in wave_result.tool_results
                    if tr.status == ToolRunStatus.FAILED
                ]
                abort_reason = f"Critical failure in wave {wave_idx}: {failed_tools}"
                logger.error("Run {} aborting — {}", run_id, abort_reason)
                break

        result.aborted = abort
        result.abort_reason = abort_reason
        result.finished_at = datetime.now(timezone.utc)

        if not self._cancelled:
            result.post_action_success = await self._run_post_actions(
                plan.post_action, run_id,
            )

        self._persist_run_state(result, current_wave=len(plan.waves), finished=True)
        self._bus.emit(
            ORCHESTRATOR_RUN_COMPLETED,
            run_id=run_id,
            success=result.success,
            aborted=result.aborted,
        )
        logger.info(
            "Run {} finished — success={}, aborted={}, duration={:.1f}s",
            run_id, result.success, result.aborted,
            (result.finished_at - started_at).total_seconds(),
        )
        return result

    def get_run_state(self) -> dict[str, Any] | None:
        """Read the persisted run state for crash recovery."""
        return self._state.get(_STATE_KEY)  # type: ignore[return-value]

    def cancel(self) -> None:
        """Request cancellation of the current run."""
        self._cancelled = True
        logger.warning("Cancellation requested — stopping running processes")
        for proc in self._running_processes:
            try:
                proc.kill()
            except (OSError, ProcessLookupError):
                pass

    async def _execute_wave(
        self,
        wave: Wave,
        wave_index: int,
        run_id: str,
    ) -> WaveResult:
        self._bus.emit(
            ORCHESTRATOR_WAVE_STARTED,
            run_id=run_id,
            wave_index=wave_index,
            label=wave.label,
            tool_count=len(wave.tools),
        )
        logger.info(
            "Wave {} ({!r}) starting — {} tool(s)",
            wave_index, wave.label or f"wave-{wave_index}", len(wave.tools),
        )

        tasks = [
            self._run_tool(tool_run, wave_index, run_id)
            for tool_run in wave.tools
        ]
        tool_results: list[ToolResult] = await asyncio.gather(*tasks)

        statuses = {tr.status for tr in tool_results}
        if all(s == ToolRunStatus.SUCCESS for s in statuses):
            wave_status = WaveStatus.COMPLETED
        elif ToolRunStatus.FAILED in statuses:
            wave_status = WaveStatus.ABORTED
        elif statuses - {ToolRunStatus.SUCCESS, ToolRunStatus.SKIPPED}:
            wave_status = WaveStatus.PARTIAL_FAILURE
        else:
            wave_status = WaveStatus.COMPLETED

        wave_result = WaveResult(
            wave_index=wave_index,
            status=wave_status,
            tool_results=tool_results,
        )

        self._bus.emit(
            ORCHESTRATOR_WAVE_COMPLETED,
            run_id=run_id,
            wave_index=wave_index,
            status=wave_status.value,
        )
        logger.info("Wave {} finished — status={}", wave_index, wave_status.value)
        return wave_result

    async def _run_tool(
        self,
        tool_run: ToolRun,
        wave_index: int,
        run_id: str,
    ) -> ToolResult:
        """Run a single tool, handling preflight, timeout, and capture."""
        tool_id = tool_run.tool_id
        result = ToolResult(tool_id=tool_id)

        config = self._registry.get(tool_id)
        if config is None:
            result.status = ToolRunStatus.PREFLIGHT_FAILED
            result.error_message = f"Tool {tool_id!r} not found in registry"
            logger.error(result.error_message)
            return result

        adapter = self._adapters.get(tool_id)
        if adapter is None:
            result.status = ToolRunStatus.PREFLIGHT_FAILED
            result.error_message = f"No adapter registered for {tool_id!r}"
            logger.error(result.error_message)
            return result

        preflight_err = await adapter.preflight(config, tool_run)
        if preflight_err is not None:
            result.status = ToolRunStatus.PREFLIGHT_FAILED
            result.error_message = preflight_err
            logger.warning("Preflight failed for {}: {}", tool_id, preflight_err)
            return result

        timeout_seconds = tool_run.timeout_minutes * 60
        result.started_at = datetime.now(timezone.utc)

        self._bus.emit(
            ORCHESTRATOR_TOOL_STARTED,
            run_id=run_id,
            wave_index=wave_index,
            tool_id=tool_id,
        )
        logger.info(
            "Tool {!r} starting (timeout={}m)", tool_id, tool_run.timeout_minutes,
        )

        try:
            process = await adapter.start(config, tool_run)
        except Exception as exc:
            result.status = ToolRunStatus.FAILED
            result.finished_at = datetime.now(timezone.utc)
            result.error_message = f"Failed to start: {exc}"
            logger.exception("Failed to start tool {!r}", tool_id)
            self._emit_tool_completed(result, run_id, wave_index)
            return result

        self._running_processes.append(process)
        output_lines: deque[str] = deque(maxlen=_LOG_TAIL_LINES)

        try:
            result = await self._poll_until_done(
                process, tool_run, config, adapter, result,
                timeout_seconds, output_lines,
            )
        finally:
            if process in self._running_processes:
                self._running_processes.remove(process)

        result.log_tail = "\n".join(output_lines)
        self._emit_tool_completed(result, run_id, wave_index)
        return result

    async def _poll_until_done(
        self,
        process: asyncio.subprocess.Process,
        tool_run: ToolRun,
        config: ToolConfig,
        adapter: BaseAdapter,
        result: ToolResult,
        timeout_seconds: int,
        output_lines: deque[str],
    ) -> ToolResult:
        """Poll the process until exit or timeout."""
        start_mono = time.monotonic()

        while True:
            if self._cancelled:
                await adapter.stop(process)
                result.status = ToolRunStatus.FAILED
                result.finished_at = datetime.now(timezone.utc)
                result.error_message = "Cancelled by user"
                return result

            await self._drain_output(process, output_lines)

            if process.returncode is not None:
                result.finished_at = datetime.now(timezone.utc)
                result.exit_code = process.returncode
                if process.returncode == 0:
                    result.status = ToolRunStatus.SUCCESS
                    logger.info(
                        "Tool {!r} exited successfully (code 0)", tool_run.tool_id,
                    )
                else:
                    result.status = ToolRunStatus.FAILED
                    result.error_message = f"Exit code {process.returncode}"
                    logger.warning(
                        "Tool {!r} failed — exit code {}",
                        tool_run.tool_id, process.returncode,
                    )
                return result

            elapsed = time.monotonic() - start_mono
            if elapsed >= timeout_seconds:
                logger.warning(
                    "Tool {!r} timed out after {:.0f}s — killing",
                    tool_run.tool_id, elapsed,
                )
                await adapter.stop(process)
                result.status = ToolRunStatus.TIMEOUT
                result.finished_at = datetime.now(timezone.utc)
                result.error_message = (
                    f"Timed out after {tool_run.timeout_minutes} minute(s)"
                )
                return result

            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    @staticmethod
    async def _drain_output(
        process: asyncio.subprocess.Process,
        output_lines: deque[str],
    ) -> None:
        """Read available lines from stdout/stderr without blocking."""
        for stream in (process.stdout, process.stderr):
            if stream is None:
                continue
            while True:
                try:
                    line = await asyncio.wait_for(
                        stream.readline(), timeout=0.05,
                    )
                except asyncio.TimeoutError:
                    break
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if decoded:
                    output_lines.append(decoded)

    async def _run_post_actions(
        self,
        post_action: PostAction,
        run_id: str,
    ) -> bool:
        logger.info(
            "Run {} — executing post-action: {}", run_id, post_action.action_type.value,
        )
        try:
            return await execute_post_action(post_action)
        except Exception:
            logger.exception("Post-action failed for run {}", run_id)
            return False

    def _emit_tool_completed(
        self,
        result: ToolResult,
        run_id: str,
        wave_index: int,
    ) -> None:
        self._bus.emit(
            ORCHESTRATOR_TOOL_COMPLETED,
            run_id=run_id,
            wave_index=wave_index,
            tool_id=result.tool_id,
            status=result.status.value,
            exit_code=result.exit_code,
            duration=result.duration_seconds,
        )

    def _persist_run_state(
        self,
        result: RunResult,
        current_wave: int,
        finished: bool = False,
    ) -> None:
        """Write run progress to StateStore for crash recovery."""
        wave_dicts = []
        for wr in result.wave_results:
            wave_dicts.append({
                "wave_index": wr.wave_index,
                "status": wr.status.value,
                "tool_results": [
                    {
                        "tool_id": tr.tool_id,
                        "status": tr.status.value,
                        "exit_code": tr.exit_code,
                        "error_message": tr.error_message,
                        "started_at": tr.started_at.isoformat() if tr.started_at else None,
                        "finished_at": tr.finished_at.isoformat() if tr.finished_at else None,
                    }
                    for tr in wr.tool_results
                ],
            })

        state_data: dict[str, Any] = {
            "run_id": result.run_id,
            "plan_name": result.plan_name,
            "current_wave": current_wave,
            "wave_results": wave_dicts,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "finished": finished,
        }
        if finished and result.finished_at:
            state_data["finished_at"] = result.finished_at.isoformat()

        self._state.set(_STATE_KEY, state_data)
