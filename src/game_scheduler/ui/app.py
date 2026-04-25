"""Standalone pywebview launcher for Game Scheduler."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Entry point for ``python -m game_scheduler.ui.app``."""
    try:
        import webview  # type: ignore[import-untyped]
    except ImportError:
        print("ERROR: pywebview is not installed. Run: pip install pywebview")
        sys.exit(1)

    from game_scheduler.run_manager import OrchestratorRunManager
    from game_scheduler.ui.api import SchedulerApi, setup_log_sink

    setup_log_sink()

    manager = OrchestratorRunManager()
    manager.start_scheduler()

    api = SchedulerApi(manager)

    # Locate the built frontend
    web_dir = Path(__file__).parent / "web"
    index_html = web_dir / "index.html"

    if index_html.exists():
        url = str(index_html)
    else:
        # Fallback: show a simple message
        url = "data:text/html,<h2>Frontend not built. Run: cd frontend && npm run build</h2>"

    window = webview.create_window(
        "Game Scheduler",
        url=url,
        js_api=api,
        width=520,
        height=760,
        min_size=(420, 600),
    )

    webview.start(debug="--debug" in sys.argv)

    manager.stop_scheduler()


if __name__ == "__main__":
    main()
