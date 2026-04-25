"""Custom exception hierarchy for gs."""
from __future__ import annotations


class GsError(Exception):
    """Base exception for all gs errors."""


class ToolNotFoundError(GsError):
    """A required tool binary was not found on disk."""

    def __init__(self, tool_id: str, searched: list[str] | None = None):
        self.tool_id = tool_id
        self.searched = searched or []
        paths = ", ".join(self.searched) if self.searched else "nowhere"
        super().__init__(f"Tool {tool_id!r} not found (searched: {paths})")


class PreflightError(GsError):
    """Pre-run health check failed for a tool."""

    def __init__(self, tool_id: str, reason: str):
        self.tool_id = tool_id
        self.reason = reason
        super().__init__(f"Preflight failed for {tool_id!r}: {reason}")


class ExecutionError(GsError):
    """A tool process failed during execution."""

    def __init__(self, tool_id: str, exit_code: int | None = None, detail: str = ""):
        self.tool_id = tool_id
        self.exit_code = exit_code
        msg = f"Tool {tool_id!r} failed"
        if exit_code is not None:
            msg += f" (exit code {exit_code})"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class ConfigReadError(GsError):
    """Failed to read an external tool's config."""

    def __init__(self, tool_id: str, path: str, reason: str):
        self.tool_id = tool_id
        self.path = path
        super().__init__(f"Cannot read config for {tool_id!r} at {path}: {reason}")


class ScheduleError(GsError):
    """Invalid schedule configuration."""
