"""Post-execution actions: kill games, shutdown, sleep."""
from __future__ import annotations

import subprocess

from loguru import logger

from gs.core.models import PostAction, PostActionKind


async def run_post_action(action: PostAction) -> bool:
    """Execute a post-action. Returns True on success."""
    handlers = {
        PostActionKind.NOTHING: _noop,
        PostActionKind.KILL_GAMES: _kill_games,
        PostActionKind.SHUTDOWN: _shutdown,
        PostActionKind.SLEEP: _sleep,
    }
    handler = handlers.get(action.kind, _noop)
    return await handler(action)


async def _noop(_: PostAction) -> bool:
    return True


async def _kill_games(action: PostAction) -> bool:
    """Kill game processes by image name."""
    for name in action.process_names:
        logger.info("Killing process: {}", name)
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", name],
                capture_output=True, timeout=10,
            )
        except Exception as e:
            logger.warning("Failed to kill {}: {}", name, e)
    return True


async def _shutdown(action: PostAction) -> bool:
    """Shutdown the PC after a delay."""
    delay = action.delay_seconds
    logger.info("Scheduling shutdown in {}s", delay)
    subprocess.run(["shutdown", "/s", "/t", str(delay)], capture_output=True)
    return True


async def _sleep(_: PostAction) -> bool:
    """Put the PC to sleep."""
    logger.info("Putting PC to sleep")
    subprocess.run(
        ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        capture_output=True,
    )
    return True
