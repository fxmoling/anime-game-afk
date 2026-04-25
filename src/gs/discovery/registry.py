"""Known tool signatures for auto-discovery.

Each entry defines how to find a tool on disk and how to launch it.
To add a new tool, add an entry to ``TOOLS``.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolSignature:
    """Everything we know about a tool before discovering it on disk."""

    tool_id: str
    name: str
    icon: str
    exe_names: list[str]            # Possible binary names (e.g. ["MAA.exe"])
    common_dirs: list[str]          # Common install directory names
    cli_template: list[str]         # Command template: {exe}, {config_name}, {task_index}
    game_processes: list[str] = field(default_factory=list)
    default_timeout_min: int = 30
    completion: str = "process_exit"  # "process_exit" or "timeout"


TOOLS: dict[str, ToolSignature] = {
    "maa": ToolSignature(
        tool_id="maa",
        name="MAA (明日方舟)",
        icon="🎯",
        exe_names=["MAA.exe", "maa.exe"],
        common_dirs=["MAA", "MaaAssistantArknights"],
        cli_template=["{exe}", "run", "{config_name}"],
        game_processes=["明日方舟.exe", "Arknights.exe"],
        default_timeout_min=60,
    ),
    "m9a": ToolSignature(
        tool_id="m9a",
        name="M9A (重返未来1999)",
        icon="🕐",
        exe_names=["MaaPiCli.exe", "MFAAvalonia.exe"],
        common_dirs=["M9A", "M9A-win-x86_64*"],
        cli_template=["{exe}", "-d"],
        game_processes=["Reverse1999.exe"],
        default_timeout_min=45,
    ),
    "okww": ToolSignature(
        tool_id="okww",
        name="ok-ww (鸣潮)",
        icon="🌊",
        exe_names=["ok-ww.exe"],
        common_dirs=["ok-ww", "ok-wuthering-waves"],
        cli_template=["{exe}", "-t", "{task_index}", "-e"],
        game_processes=["Wuthering Waves.exe", "Client-Win64-Shipping.exe"],
        default_timeout_min=45,
    ),
    "bettergi": ToolSignature(
        tool_id="bettergi",
        name="BetterGI (原神)",
        icon="🎮",
        exe_names=["BetterGI.exe", "BetterGenshinImpact.exe"],
        common_dirs=["BetterGI", "better-genshin-impact", "BetterGenshinImpact"],
        cli_template=["{exe}", "startOneDragon", "{config_name}"],
        game_processes=["YuanShen.exe", "GenshinImpact.exe"],
        default_timeout_min=60,
        completion="timeout",
    ),
    "zzz": ToolSignature(
        tool_id="zzz",
        name="ZZZ (绝区零)",
        icon="⚡",
        exe_names=[
            "OneDragon-Launcher.exe",
            "ZenlessZoneZero-OneDragon.exe",
        ],
        common_dirs=[
            "ZenlessZoneZero-OneDragon",
            "zzz-onedragon",
            "OneDragon",
        ],
        cli_template=["{exe}", "-o", "--close-game"],
        game_processes=["ZenlessZoneZero.exe"],
        default_timeout_min=45,
    ),
    "aether": ToolSignature(
        tool_id="aether",
        name="深空之眼 AFK",
        icon="👁",
        exe_names=["aether-gazer-afk.exe", "anime-game-afk.exe"],
        common_dirs=["aether-gazer-afk", "anime-game-afk"],
        cli_template=["{exe}", "--daily"],
        game_processes=["AetherGazer.exe"],
        default_timeout_min=30,
    ),
}
