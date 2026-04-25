# CLAUDE.md - Game Scheduler Project Configuration

## Project Overview

多游戏自动化编排器 — 定时调度多个游戏自动化工具的每日任务。

## Architecture

```
src/game_scheduler/
├── models.py           # 数据模型 (ToolConfig, RunPlan, Wave, ScheduleEntry)
├── dag_executor.py     # DAG 执行引擎 (sequential waves of parallel tools)
├── scheduler.py        # croniter 定时调度 + Windows Task Scheduler 唤醒
├── config_manager.py   # YAML 配置管理
├── run_manager.py      # 顶层管理器
├── post_actions.py     # 关游戏/关机/休眠
├── adapters/           # 工具适配器
│   ├── base.py         # ToolAdapter Protocol + BaseAdapter
│   ├── maa.py          # MAA: maa run <task>
│   ├── m9a.py          # M9A: MaaPiCli -d
│   ├── okww.py         # ok-ww: ok-ww.exe -t N -e
│   ├── bettergi.py     # BetterGI: startOneDragon
│   ├── zzz.py          # ZZZ: exe -o --close-game
│   ├── aether_gazer.py # aether-gazer-afk
│   └── generic.py      # 通用 exe 启动器
├── runtime/
│   ├── events.py       # EventBus
│   └── state.py        # StateStore
└── ui/
    ├── api.py          # SchedulerApi (pywebview)
    ├── app.py          # GUI 启动入口
    └── web/            # Vue 3 构建产物
```

## Supported Tools (verified CLI commands)

| Tool | Command | Completion |
|------|---------|------------|
| MAA | `maa run daily` | Exit code |
| M9A | `MaaPiCli.exe -d` | Process exit |
| ok-ww | `ok-ww.exe -t 1 -e` | Process exit |
| BetterGI | `BetterGI.exe startOneDragon "config"` | Timeout+kill |
| ZZZ | `exe -o --close-game` | Process exit |
| aether-gazer-afk | `exe --daily` | Process exit |

## Development

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m game_scheduler.ui.app --debug
cd frontend && npm install && npm run build
```

## Coding Standards

- Python 3.11+, `from __future__ import annotations`
- loguru for logging, type hints everywhere
- asyncio for concurrent tool execution
- Vue 3 Composition API, Chinese language UI
