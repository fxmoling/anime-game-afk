"""Background scheduler: check cron expressions, trigger runs."""
from __future__ import annotations

import threading
import time
from datetime import datetime

from loguru import logger

from gs.core.cron import matches_now


class Scheduler:
    """Background thread that fires plans on cron schedules.

    Usage::

        scheduler = Scheduler(get_schedules=fn, on_fire=fn)
        scheduler.start()
        ...
        scheduler.stop()
    """

    def __init__(
        self,
        get_schedules,  # Callable[[], list[Schedule]]
        on_fire,        # Callable[[Schedule], None]
        interval: int = 60,
    ) -> None:
        self._get_schedules = get_schedules
        self._on_fire = on_fire
        self._interval = interval
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_fired: set[str] = set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        logger.info("Scheduler started (interval={}s)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now()
            minute_key = now.strftime("%Y%m%d%H%M")

            try:
                for sched in self._get_schedules():
                    if not sched.enabled:
                        continue
                    fire_key = f"{sched.id}:{minute_key}"
                    if fire_key in self._last_fired:
                        continue
                    if matches_now(sched.cron, now):
                        logger.info("Firing schedule: {} ({})", sched.name, sched.cron)
                        self._last_fired.add(fire_key)
                        self._on_fire(sched)
            except Exception:
                logger.exception("Scheduler loop error")

            # Clean old fire keys (keep last 100)
            if len(self._last_fired) > 100:
                self._last_fired = set(list(self._last_fired)[-50:])

            self._stop_event.wait(self._interval)
