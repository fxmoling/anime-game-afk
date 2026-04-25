"""Tool adapter implementations.

Registry mapping tool_id → concrete adapter class.
"""
from __future__ import annotations

from .base import BaseAdapter, ToolAdapter
from .bettergi import BetterGiAdapter
from .generic import GenericAdapter
from .m9a import M9aAdapter
from .maa import MaaAdapter
from .okww import OkwwAdapter
from .zzz import ZzzAdapter
from .aether_gazer import AetherGazerAdapter

__all__ = [
    "BaseAdapter",
    "BetterGiAdapter",
    "GenericAdapter",
    "M9aAdapter",
    "MaaAdapter",
    "OkwwAdapter",
    "ToolAdapter",
    "ZzzAdapter",
    "AetherGazerAdapter",
    "get_adapter",
]

_REGISTRY: dict[str, type[BaseAdapter]] = {
    "maa": MaaAdapter,
    "m9a": M9aAdapter,
    "okww": OkwwAdapter,
    "bettergi": BetterGiAdapter,
    "zzz": ZzzAdapter,
    "aether": AetherGazerAdapter,
    "generic": GenericAdapter,
}


def get_adapter(tool_id: str) -> BaseAdapter:
    """Return the adapter instance for *tool_id*, falling back to generic."""
    cls = _REGISTRY.get(tool_id, GenericAdapter)
    return cls()
