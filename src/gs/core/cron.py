"""Cron expression utilities.

Thin wrapper around ``croniter`` with a fallback for when it's not installed.
"""
from __future__ import annotations

from datetime import datetime


def next_fire_time(cron_expr: str, base: datetime | None = None) -> datetime:
    """Return the next fire time for *cron_expr* after *base* (default: now)."""
    base = base or datetime.now()
    try:
        from croniter import croniter  # type: ignore[import-untyped]
        return croniter(cron_expr, base).get_next(datetime)
    except ImportError:
        return _simple_next(cron_expr, base)


def matches_now(cron_expr: str, now: datetime | None = None) -> bool:
    """Return True if *cron_expr* matches the current minute."""
    now = now or datetime.now()
    try:
        from croniter import croniter
        return croniter.match(cron_expr, now)
    except ImportError:
        return _simple_match(cron_expr, now)


# ---------------------------------------------------------------------------
# Fallback: parse "M H * * *" without croniter
# ---------------------------------------------------------------------------

def _simple_next(expr: str, base: datetime) -> datetime:
    """Parse simple ``minute hour * * *`` patterns."""
    parts = expr.split()
    if len(parts) < 2:
        raise ValueError(f"Cannot parse cron expression: {expr!r}")
    minute, hour = int(parts[0]), int(parts[1])
    candidate = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= base:
        from datetime import timedelta
        candidate += timedelta(days=1)
    return candidate


def _simple_match(expr: str, now: datetime) -> bool:
    parts = expr.split()
    if len(parts) < 2:
        return False
    minute, hour = int(parts[0]), int(parts[1])
    return now.hour == hour and now.minute == minute
