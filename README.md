# 🎮 Game Scheduler — 多游戏自动化编排器

一键调度多个游戏自动化工具，定时执行每日任务。

## 支持的工具

| 工具 | 游戏 | 调用方式 |
|------|------|---------|
| MAA | 明日方舟 | `maa run daily` |
| ok-ww | 鸣潮 | `ok-ww.exe -t 1 -e` |
| BetterGI | 原神 | `BetterGI.exe startOneDragon` |
| M9A | 重返未来1999 | `MaaPiCli.exe -d` |
| ZZZ-OneDragon | 绝区零 | `exe -o --close-game` |
| aether-gazer-afk | 深空之眼 | `exe --daily` |

## 功能

- 📅 定时执行（每天凌晨自动跑日常）
- 🔄 串并行编排（步骤内并行，步骤间串行）
- 🎮 游戏卡片式 UI（萌新友好）
- ⚡ 完成后自动关游戏/关机

## 安装

```bash
pip install -r requirements.txt
python -m game_scheduler.ui.app
```

## 开发

```bash
# 前端开发
cd frontend
npm install
npm run dev

# 构建前端
npm run build
```

## 架构

```
src/game_scheduler/
├── models.py          # 数据模型（工具配置、执行计划、调度条目）
├── dag_executor.py    # DAG 执行引擎（串行波次，波内并行）
├── scheduler.py       # Cron 调度器 + Windows 唤醒任务
├── config_manager.py  # YAML 配置管理
├── run_manager.py     # 高层编排管理器（API 层调用入口）
├── post_actions.py    # 完成后动作（关游戏/关机/休眠）
├── adapters/          # 各工具适配器
│   ├── maa.py         # MAA (明日方舟)
│   ├── m9a.py         # M9A (重返未来1999)
│   ├── okww.py        # ok-ww (鸣潮)
│   ├── bettergi.py    # BetterGI (原神)
│   ├── zzz.py         # ZZZ-OneDragon (绝区零)
│   ├── aether_gazer.py # aether-gazer-afk (深空之眼)
│   └── generic.py     # 通用适配器
├── runtime/           # 轻量运行时
│   ├── events.py      # 事件总线
│   └── state.py       # 持久化状态存储
└── ui/
    ├── api.py         # pywebview API
    ├── app.py         # 启动入口
    └── web/           # Vue 3 构建产物
```
