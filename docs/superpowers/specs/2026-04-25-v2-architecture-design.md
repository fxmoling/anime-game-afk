# Game Scheduler v2 — Architecture Redesign

**Date**: 2026-04-25
**Status**: Design

## Problem

Build a beginner-friendly multi-game automation scheduler that:
1. Auto-discovers installed game scripts on first launch
2. Reads/edits external tool configs (MAA-style config injection)
3. Schedules serial+parallel execution of daily tasks
4. Hot-updates itself transparently
5. Maintains clean, extensible code for rapid iteration

## Key Decisions

- **Tech stack**: Python 3.11+ (pywebview + Vue 3) + self-built launcher for hot-update
- **Config strategy**: Level 1 (read-only) for all tools v1, Level 2 (read+write) for MAA first, then ok-ww
- **Scope**: 6 tools initially (MAA, M9A, ok-ww, BetterGI, ZZZ, aether-gazer-afk), extensible to any
- **Rewrite**: Full clean rewrite of game_scheduler package. Code quality > speed.

## Architecture Overview

```
game-scheduler/
├── launcher.py              # Thin launcher: check update → download → start app
├── src/
│   └── gs/                  # Main package (short name for clean imports)
│       ├── core/            # Layer 0: Pure data + utilities (zero I/O)
│       │   ├── models.py    # Dataclasses: Tool, Plan, Wave, Schedule, Result
│       │   ├── cron.py      # Cron expression parsing (wraps croniter)
│       │   └── errors.py    # Custom exception hierarchy
│       │
│       ├── discovery/       # Layer 1: Find installed tools on disk
│       │   ├── scanner.py   # Scan filesystem for known tools
│       │   ├── registry.py  # Known tool signatures (exe names, paths, registry keys)
│       │   └── health.py    # Preflight checks (exe exists, deps met)
│       │
│       ├── config/          # Layer 2: Read/write external tool configs
│       │   ├── base.py      # ConfigAdapter protocol
│       │   ├── maa.py       # MAA gui.json reader/writer
│       │   ├── okww.py      # ok-ww configs/ reader (future: writer)
│       │   ├── bettergi.py  # BetterGI User/config.json reader
│       │   ├── zzz.py       # ZZZ YAML config reader
│       │   ├── m9a.py       # M9A interface.json reader
│       │   └── generic.py   # Fallback: no config awareness
│       │
│       ├── execution/       # Layer 3: Launch and monitor tool processes
│       │   ├── launcher.py  # Start subprocess, build CLI args
│       │   ├── monitor.py   # Poll process, detect completion
│       │   ├── dag.py       # DAG executor (waves of parallel tools)
│       │   └── post.py      # Post-actions (kill games, shutdown, sleep)
│       │
│       ├── schedule/        # Layer 4: Time-based triggers
│       │   ├── scheduler.py # Background cron loop
│       │   └── wake.py      # Windows Task Scheduler integration
│       │
│       ├── store/           # Persistence layer
│       │   ├── settings.py  # App settings (YAML)
│       │   ├── state.py     # Runtime state (JSON, crash recovery)
│       │   └── history.py   # Run history / logs
│       │
│       ├── update/          # Self-update system
│       │   ├── checker.py   # Check GitHub releases for new version
│       │   ├── downloader.py # Download + extract update zip
│       │   └── patcher.py   # Replace files + restart
│       │
│       └── api/             # UI interface layer
│           ├── server.py    # pywebview app entry point
│           ├── handlers.py  # API methods (exposed to JS)
│           └── push.py      # Server → client push (evaluate_js)
│
├── frontend/                # Vue 3 SPA
│   └── src/
│       ├── App.vue
│       ├── views/           # SchedulerView, SettingsView, LogsView
│       ├── components/      # GameCard, StepEditor, ToolPicker, etc.
│       └── composables/     # useApi, useStore, useOrchestrator
│
├── config/
│   └── defaults.yaml        # Default tool registry + app settings
│
└── tests/                   # Unit + integration tests
```

## Layer Dependency Rules

```
Layer 0 (core)      → depends on: nothing
Layer 1 (discovery) → depends on: core
Layer 2 (config)    → depends on: core
Layer 3 (execution) → depends on: core, discovery, config
Layer 4 (schedule)  → depends on: core, execution
store               → depends on: core
update              → depends on: nothing (standalone)
api                 → depends on: everything above (thin façade)
```

**Hard rule**: No circular dependencies. Lower layers never import higher layers.

## Module Specifications

### core/models.py — Pure Data

Small, focused dataclasses. All JSON-serializable.

```python
@dataclass
class ToolInfo:
    """A registered automation tool."""
    tool_id: str          # "maa", "okww", etc.
    name: str             # "MAA (明日方舟)"
    exe_path: str         # Absolute path to executable
    install_dir: str      # Tool's root directory
    version: str          # Detected version
    status: ToolStatus    # ready / not_found / error
    icon: str             # Emoji

@dataclass
class TaskConfig:
    """Per-tool task selection for one run."""
    tool_id: str
    timeout_min: int = 30
    cli_args: list[str] = field(default_factory=list)
    # For tools with config awareness:
    tasks_enabled: dict[str, bool] | None = None  # task_name → enabled
    config_overrides: dict[str, Any] | None = None

@dataclass
class Wave:
    """Parallel group: all tasks start simultaneously."""
    tasks: list[TaskConfig]

@dataclass
class Plan:
    """Execution plan: sequential waves."""
    name: str
    waves: list[Wave]
    post_action: PostAction

@dataclass
class Schedule:
    """Cron-triggered plan."""
    id: str
    name: str
    cron: str
    plan: Plan
    enabled: bool
```

### discovery/scanner.py — Auto-Find Tools

```python
class ToolScanner:
    """Discover installed game automation tools."""

    def scan_all(self) -> list[ToolInfo]:
        """Scan common paths for all known tools."""

    def scan_tool(self, tool_id: str) -> ToolInfo | None:
        """Scan for a specific tool."""
```

**Scan strategies** (per tool, from registry.py):
1. Check running processes (fastest)
2. Check desktop shortcuts / Start menu
3. Check common install paths (C:/MAA, D:/MAA, etc.)
4. Check Windows registry (for tools that register)
5. Glob search known drive roots

### config/base.py — Config Adapter Protocol

```python
class ConfigAdapter(Protocol):
    """Read/write external tool configuration."""

    tool_id: str

    def can_read(self) -> bool:
        """Whether this adapter can read the tool's config."""

    def read_tasks(self, install_dir: str) -> list[TaskOption]:
        """Read available tasks from tool's config files."""

    def read_settings(self, install_dir: str) -> dict[str, Any]:
        """Read tool-specific settings (for display in our UI)."""

    def write_settings(self, install_dir: str, settings: dict) -> None:
        """Write modified settings back to tool's config files."""
        # Level 2 only. Level 1 adapters raise NotImplementedError.
```

**TaskOption**: `{id, name, enabled, description, category}` — normalized across all tools.

### config/maa.py — MAA Config (Level 2)

Read from `MAA/config/gui.json` + `gui.new.json`:
- Available tasks: StartUp, Fight, Recruit, Infrast, Mall, Award, Roguelike, CloseDown
- Per-task settings: stage, medicine, times, etc.
- Connection settings: ADB address, emulator type

Write back: modify gui.json fields → save. (Same pattern as AUTO-MAS)

### execution/launcher.py — Build CLI + Start Process

```python
class ToolLauncher:
    """Build CLI command and start tool subprocess."""

    def build_command(self, tool: ToolInfo, task: TaskConfig) -> list[str]:
        """Build the CLI command for a tool run."""

    def start(self, tool: ToolInfo, task: TaskConfig) -> Process:
        """Launch tool and return process handle."""
```

Tool-specific CLI is defined in a **command template** per tool (in registry.py), not in individual adapter classes:

```python
TOOL_COMMANDS = {
    "maa": {"template": ["{exe}", "run", "{config_name}"], "default_config": "daily"},
    "okww": {"template": ["{exe}", "-t", "{task_index}", "-e"], "default_task_index": "1"},
    "bettergi": {"template": ["{exe}", "startOneDragon", "{config_name}"]},
    "m9a": {"template": ["{exe}", "-d"]},
    "zzz": {"template": ["{exe}", "-o", "--close-game"]},
    "aether": {"template": ["{exe}", "--daily"]},
}
```

### execution/dag.py — Wave-Based DAG

```python
class DagExecutor:
    """Execute Plan as sequential waves of parallel tasks."""

    async def run(self, plan: Plan) -> RunResult:
        for wave in plan.waves:
            results = await asyncio.gather(
                *[self._run_task(t) for t in wave.tasks]
            )
            # persist after each wave for crash recovery
```

### update/checker.py — Hot Update

```python
class UpdateChecker:
    """Check GitHub releases, download, and apply updates."""

    def check(self) -> UpdateInfo | None:
        """Check if a newer version exists."""

    async def download(self, info: UpdateInfo) -> Path:
        """Download update zip to temp dir."""

    def apply(self, zip_path: Path) -> None:
        """Extract and replace app files. Called by launcher on restart."""
```

**Update flow**:
1. `launcher.py` starts → checks for pending update in `data/pending_update/`
2. If pending: apply update (replace files) → start app
3. If not: start app normally
4. App runs → background check for new version → download to `data/pending_update/`
5. Next restart: launcher applies it

### api/handlers.py — Thin API Façade

```python
class ApiHandlers:
    """All methods callable from JS frontend."""

    # Discovery
    def scan_tools(self) -> list[dict]: ...
    def get_tools(self) -> list[dict]: ...

    # Config
    def get_tool_tasks(self, tool_id: str) -> list[dict]: ...
    def get_tool_settings(self, tool_id: str) -> dict: ...
    def save_tool_settings(self, tool_id: str, settings: dict) -> dict: ...

    # Schedules
    def get_schedules(self) -> list[dict]: ...
    def save_schedule(self, schedule: dict) -> dict: ...
    def delete_schedule(self, schedule_id: str) -> dict: ...

    # Execution
    def run_plan(self, plan: dict) -> dict: ...
    def stop(self) -> dict: ...
    def get_status(self) -> dict: ...

    # Update
    def check_update(self) -> dict: ...
```

## File Size Guidelines

| File | Target LOC | Max LOC |
|------|-----------|---------|
| Each model/dataclass file | 50-100 | 150 |
| Each config adapter | 80-150 | 250 |
| Each discovery module | 50-100 | 150 |
| DAG executor | 100-150 | 200 |
| API handlers | 80-120 | 150 |
| Each Vue component | 50-150 | 300 |

**If a file exceeds max LOC, split it.**

## Implementation Phases

### Phase 1: Core + Discovery + Execution (functional MVP)
- core/models.py, errors.py
- discovery/scanner.py, registry.py, health.py
- execution/launcher.py, monitor.py, dag.py, post.py
- store/settings.py, state.py
- Minimal CLI test harness (no UI yet)

### Phase 2: Config Adapters
- config/base.py + maa.py (Level 2: read+write)
- config/okww.py, bettergi.py, zzz.py, m9a.py (Level 1: read-only)

### Phase 3: Schedule + API + Frontend
- schedule/scheduler.py, wake.py
- api/server.py, handlers.py, push.py
- Vue frontend (SchedulerView, SettingsView, LogsView)
- localhost dev server for testing

### Phase 4: Update + Polish
- update/checker.py, downloader.py, patcher.py
- launcher.py
- Error handling, logging, edge cases
- README, docs, memory files

## Testing Strategy

- **Unit tests**: core/, config/ (mock filesystem)
- **Integration tests**: discovery/ (real filesystem scan), execution/ (mock subprocess)
- **E2E tests**: localhost web page → API → execution (mock tools)
- **No PyInstaller in dev**: use `python -m gs.api.server` for development
