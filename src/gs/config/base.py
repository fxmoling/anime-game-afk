"""Config adapter protocol: read/write external tool configurations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class TaskOption:
    """A task/feature that can be enabled/disabled in a tool."""

    id: str
    name: str
    enabled: bool = True
    description: str = ""
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "description": self.description,
            "category": self.category,
        }


class ConfigAdapter(Protocol):
    """Read (and optionally write) an external tool's configuration."""

    tool_id: str

    def can_read(self) -> bool:
        """Whether this adapter can read the tool's config."""
        ...

    def can_write(self) -> bool:
        """Whether this adapter can write back to the tool's config."""
        ...

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        """Read available tasks from the tool's config files."""
        ...

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        """Read tool-specific settings for display in our UI."""
        ...

    def write_settings(self, install_dir: str, settings: dict[str, Any]) -> None:
        """Write modified settings back to the tool's config files."""
        ...


class NullAdapter:
    """Fallback adapter for tools with no config awareness."""

    tool_id = "generic"

    def can_read(self) -> bool:
        return False

    def can_write(self) -> bool:
        return False

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        return []

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        return {}

    def write_settings(self, install_dir: str, settings: dict[str, Any]) -> None:
        pass
