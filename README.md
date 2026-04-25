# 🎮 Game Scheduler — 多游戏自动化编排器

一键调度多个游戏自动化工具，定时执行每日任务。

## 支持的工具

| 工具 | 游戏 | 调用方式 | 配置读取 |
|------|------|---------|---------|
| MAA | 明日方舟 | `maa run daily` | ✅ 读写 |
| M9A | 重返未来1999 | `MaaPiCli -d` | ✅ 只读 |
| ok-ww | 鸣潮 | `ok-ww.exe -t 1 -e` | ✅ 只读 |
| BetterGI | 原神 | `startOneDragon` | ✅ 只读 |
| ZZZ-OneDragon | 绝区零 | `exe -o --close-game` | ✅ 只读 |
| aether-gazer-afk | 深空之眼 | `exe --daily` | 计划中 |

## 功能

- 📅 定时执行（每天凌晨自动跑日常）
- 🔄 串并行编排（步骤内并行，步骤间串行）
- 🔍 自动发现已安装的游戏脚本
- 📖 读取/编辑外部工具配置
- ⚡ 完成后自动关游戏/关机

## 开发

```bash
pip install -r requirements.txt flask
cd anime-game-afk

# 开发模式 (Flask localhost:5000)
PYTHONPATH=src python -m gs.api.server

# API 测试
curl http://localhost:5000/api/tools
curl http://localhost:5000/api/tools/okww/tasks
```

## 架构

```
src/gs/
├── core/        # 纯数据模型 (无 I/O)
├── discovery/   # 自动发现已安装工具
├── config/      # 读写外部工具配置
├── execution/   # 启动进程 + DAG 执行
├── schedule/    # 定时调度
├── store/       # 持久化 (YAML + JSON)
├── update/      # 自动更新 (计划中)
└── api/         # Web API (Flask dev / pywebview prod)
```

## License

MIT
