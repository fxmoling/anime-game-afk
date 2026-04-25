"""Cron-based scheduler for triggering RunPlan execution.

Runs in a background thread, checks every 60 seconds if any
ScheduleEntry's cron expression matches the current time.
"""
from __future__ import annotations

import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger

if TYPE_CHECKING:
    from game_scheduler.config_manager import OrchestratorConfigManager
    from game_scheduler.models import ScheduleEntry

# ---------------------------------------------------------------------------
# croniter availability
# ---------------------------------------------------------------------------

try:
    from croniter import croniter as _croniter  # type: ignore[import-untyped]

    _HAS_CRONITER = True
except ImportError:  # pragma: no cover
    _HAS_CRONITER = False
    _croniter = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHECK_INTERVAL_SECONDS = 60
_WAKE_TASK_PREFIX = "GameScheduler_Wake_"


# ---------------------------------------------------------------------------
# Cron helpers
# ---------------------------------------------------------------------------

def _next_fire_time(cron_expr: str, base: datetime | None = None) -> datetime | None:
    """Calculate the next fire time for *cron_expr*."""
    now = base or datetime.now()

    if _HAS_CRONITER:
        try:
            cron = _croniter(cron_expr, now)
            return cron.get_next(datetime)  # type: ignore[return-value]
        except (ValueError, KeyError) as exc:
            logger.warning("Invalid cron expression {!r}: {}", cron_expr, exc)
            return None

    # Fallback: parse "minute hour * * *"
    try:
        parts = cron_expr.strip().split()
        minute = int(parts[0])
        hour = int(parts[1])
    except (IndexError, ValueError):
        logger.warning("Cannot parse cron expression without croniter: {!r}", cron_expr)
        return None

    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        from datetime import timedelta

        candidate += timedelta(days=1)
    return candidate


def _cron_matches_now(cron_expr: str, now: datetime) -> bool:
    """Return True if *now* falls within the cron expression's current minute."""
    if _HAS_CRONITER:
        try:
            cron = _croniter(cron_expr, now.replace(second=0, microsecond=0))
            prev: datetime = cron.get_prev(datetime)  # type: ignore[assignment]
            return (
                prev.year == now.year
                and prev.month == now.month
                and prev.day == now.day
                and prev.hour == now.hour
                and prev.minute == now.minute
            )
        except (ValueError, KeyError):
            return False

    # Fallback
    try:
        parts = cron_expr.strip().split()
        minute = int(parts[0])
        hour = int(parts[1])
        return now.hour == hour and now.minute == minute
    except (IndexError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Windows Task Scheduler wake integration
# ---------------------------------------------------------------------------

def register_wake_task(schedule_id: str, cron_expr: str) -> bool:
    """Register a Windows scheduled task to wake the PC."""
    next_time = _next_fire_time(cron_expr)
    if next_time is None:
        logger.warning("Cannot register wake task — invalid cron: {}", cron_expr)
        return False

    task_name = f"{_WAKE_TASK_PREFIX}{schedule_id}"
    time_str = next_time.strftime("%H:%M")

    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", "cmd /c echo GameScheduler wake trigger",
        "/SC", "DAILY",
        "/ST", time_str,
        "/F",
        "/RL", "HIGHEST",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=15,
        )
        if result.returncode == 0:
            logger.info("Registered wake task {} at {}", task_name, time_str)
            _enable_wake_to_run(task_name)
            return True
        logger.warning(
            "schtasks /Create failed (code {}): {}",
            result.returncode,
            result.stderr.strip(),
        )
        return False
    except FileNotFoundError:
        logger.error("schtasks not found — cannot register wake task")
        return False
    except subprocess.TimeoutExpired:
        logger.error("schtasks timed out registering wake task")
        return False
    except Exception:
        logger.exception("Failed to register wake task {}", task_name)
        return False


def _enable_wake_to_run(task_name: str) -> None:
    """Enable the WakeToRun setting on an existing scheduled task."""
    try:
        subprocess.run(
            ["schtasks", "/Change", "/TN", task_name, "/ENABLE"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10,
        )
    except Exception:
        pass


def unregister_wake_task(schedule_id: str) -> bool:
    """Remove the Windows wake task for *schedule_id*."""
    task_name = f"{_WAKE_TASK_PREFIX}{schedule_id}"
    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", task_name, "/F"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("Removed wake task {}", task_name)
            return True
        logger.debug("schtasks /Delete {}: {}", task_name, result.stderr.strip())
        return False
    except Exception:
        logger.exception("Failed to remove wake task {}", task_name)
        return False


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Cron-based scheduler for triggering RunPlans."""

    def __init__(
        self,
        config_manager: OrchestratorConfigManager,
        executor_factory: Callable[[], Any],
    ) -> None:
        self._config = config_manager
        self._executor_factory = executor_factory
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_fired: dict[str, str] = {}

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Scheduler already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="game-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("Scheduler started (interval={}s)", _CHECK_INTERVAL_SECONDS)

    def stop(self) -> None:
        """Stop the background scheduler thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_next_run(self, schedule_id: str) -> datetime | None:
        for entry in self._config.get_schedules():
            if entry.schedule_id == schedule_id:
                return _next_fire_time(entry.cron_expr)
        return None

    def run_now(self, schedule_id: str) -> bool:
        """Manually trigger a schedule immediately."""
        for entry in self._config.get_schedules():
            if entry.schedule_id == schedule_id:
                logger.info("Manual trigger for schedule {!r}", entry.name)
                self._fire(entry)
                return True
        logger.warning("Schedule {} not found for manual trigger", schedule_id)
        return False

    def _loop(self) -> None:
        logger.debug("Scheduler loop entered")
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Scheduler tick failed")
            self._stop_event.wait(timeout=_CHECK_INTERVAL_SECONDS)
        logger.debug("Scheduler loop exiting")

    def _tick(self) -> None:
        now = datetime.now()
        minute_key = now.strftime("%Y-%m-%d %H:%M")

        for entry in self._config.get_schedules():
            if not entry.enabled:
                continue
            if self._last_fired.get(entry.schedule_id) == minute_key:
                continue
            if _cron_matches_now(entry.cron_expr, now):
                logger.info(
                    "Schedule {!r} ({}) triggered at {}",
                    entry.name, entry.schedule_id, minute_key,
                )
                self._last_fired[entry.schedule_id] = minute_key
                self._fire(entry)

    def _fire(self, entry: ScheduleEntry) -> None:
        import asyncio

        def _run() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                executor = self._executor_factory()
                loop.run_until_complete(executor.execute(entry.plan))
            except Exception:
                logger.exception(
                    "Failed to execute schedule {!r}", entry.name,
                )
            finally:
                try:
                    entry.last_run = datetime.now(timezone.utc).isoformat()
                    self._config.save_schedule(entry)
                except Exception:
                    logger.exception("Failed to update last_run for {}", entry.schedule_id)

        thread = threading.Thread(
            target=_run,
            name=f"sched-run-{entry.schedule_id}",
            daemon=True,
        )
        thread.start()
