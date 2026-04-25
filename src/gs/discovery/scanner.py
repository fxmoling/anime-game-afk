"""Scan the filesystem for installed game automation tools."""
from __future__ import annotations

import glob
import os
from pathlib import Path

from loguru import logger

from gs.core.models import ToolInfo, ToolStatus
from gs.discovery.registry import TOOLS, ToolSignature


# Drives and roots to search
_SEARCH_ROOTS = ["C:\\", "D:\\", "E:\\", "F:\\"]
_DESKTOP = Path.home() / "Desktop"
_COMMON_PARENTS = [
    _DESKTOP,
    Path.home(),
    Path("C:\\Program Files"),
    Path("C:\\Program Files (x86)"),
    Path("D:\\"),
    Path("E:\\"),
]


class ToolScanner:
    """Discover installed automation tools on this machine."""

    def scan_all(self) -> list[ToolInfo]:
        """Scan for all known tools. Returns a ToolInfo per registered tool."""
        results = []
        for sig in TOOLS.values():
            info = self.scan_tool(sig)
            results.append(info)
        return results

    def scan_tool(self, sig: ToolSignature) -> ToolInfo:
        """Try to find a specific tool on disk."""
        logger.debug("Scanning for {}", sig.tool_id)

        for strategy in [self._find_in_common_parents, self._find_by_glob]:
            path = strategy(sig)
            if path:
                logger.info("Found {} at {}", sig.tool_id, path)
                return ToolInfo(
                    tool_id=sig.tool_id,
                    name=sig.name,
                    exe_path=str(path),
                    install_dir=str(path.parent),
                    status=ToolStatus.READY,
                    icon=sig.icon,
                )

        logger.debug("{} not found", sig.tool_id)
        return ToolInfo(
            tool_id=sig.tool_id,
            name=sig.name,
            status=ToolStatus.NOT_FOUND,
            icon=sig.icon,
        )

    @staticmethod
    def _find_in_common_parents(sig: ToolSignature) -> Path | None:
        """Check common parent directories for tool folders."""
        for parent in _COMMON_PARENTS:
            if not parent.exists():
                continue
            for dir_pattern in sig.common_dirs:
                for match in parent.glob(dir_pattern):
                    if not match.is_dir():
                        continue
                    for exe_name in sig.exe_names:
                        exe = match / exe_name
                        if exe.is_file():
                            return exe
        return None

    @staticmethod
    def _find_by_glob(sig: ToolSignature) -> Path | None:
        """Broader search: scan drive roots one level deep."""
        for root in _SEARCH_ROOTS:
            if not os.path.isdir(root):
                continue
            for dir_pattern in sig.common_dirs:
                pattern = os.path.join(root, dir_pattern)
                for match in glob.glob(pattern):
                    match_path = Path(match)
                    if not match_path.is_dir():
                        continue
                    for exe_name in sig.exe_names:
                        exe = match_path / exe_name
                        if exe.is_file():
                            return exe
        return None
