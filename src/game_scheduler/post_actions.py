"""Post-action executors for the orchestrator.

Post-actions run after all waves complete (or after an abort).
They handle cleanup tasks like killing game processes, shutting down,
or putting the PC to sleep.
"""
from __future__ import annotations

import asyncio
import subprocess

from loguru import logger

from game_scheduler.models import PostAction, PostActionType


async def execute_post_action(action: PostAction) -> bool:
    """Execute a post-action. Returns ``True`` on success."""
    dispatch = {
        PostActionType.NOTHING: _do_nothing,
        PostActionType.KILL_GAMES: _kill_game_processes,
        PostActionType.SHUTDOWN: _shutdown_pc,
        PostActionType.SLEEP: _sleep_pc,
    }
    handler = dispatch.get(action.action_type)
    if handler is None:
        logger.error("Unknown post-action type: {}", action.action_type)
        return False

    return await handler(action)


async def _do_nothing(action: PostAction) -> bool:
    logger.debug("Post-action: nothing to do")
    return True


async def _kill_game_processes(action: PostAction) -> bool:
    """Kill game processes by image name via ``taskkill /F /IM``."""
    if not action.process_names:
        logger.debug("No process names configured for kill_games — skipping")
        return True

    all_ok = True
    for name in action.process_names:
        logger.info("Killing process: {}", name)
        try:
            proc = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/IM", name,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                logger.info("Killed {}", name)
            elif proc.returncode == 128:
                logger.debug("{} was not running", name)
            else:
                msg = stderr.decode("utf-8", errors="replace").strip()
                if "not found" in msg.lower():
                    logger.debug("{} was not running", name)
                else:
                    logger.warning("taskkill {} returned {}: {}", name, proc.returncode, msg)
                    all_ok = False
        except FileNotFoundError:
            logger.error("taskkill not found — cannot kill {}", name)
            all_ok = False
        except Exception:
            logger.exception("Error killing process {}", name)
            all_ok = False

    return all_ok


async def _shutdown_pc(action: PostAction) -> bool:
    """Schedule a system shutdown via ``shutdown /s /t <delay>``."""
    delay = action.delay_seconds
    logger.warning("Scheduling PC shutdown in {} seconds", delay)
    try:
        proc = await asyncio.create_subprocess_exec(
            "shutdown", "/s", "/t", str(delay),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _, stderr = await proc.communicate()

        if proc.returncode == 0:
            logger.warning("Shutdown scheduled — PC will turn off in {}s", delay)
            return True

        msg = stderr.decode("utf-8", errors="replace").strip()
        logger.error("shutdown command failed (code {}): {}", proc.returncode, msg)
        return False
    except Exception:
        logger.exception("Failed to schedule shutdown")
        return False


async def _sleep_pc(action: PostAction) -> bool:
    """Put the PC to sleep via ``rundll32 powrprof.dll,SetSuspendState``."""
    logger.warning("Putting PC to sleep")
    try:
        proc = await asyncio.create_subprocess_exec(
            "rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        await proc.communicate()
        logger.info("Sleep command issued")
        return True
    except Exception:
        logger.exception("Failed to put PC to sleep")
        return False
