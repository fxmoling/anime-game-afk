"""Dev server: localhost Flask app for testing without pywebview."""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from loguru import logger

from gs.api.handlers import ApiHandlers

app = Flask(__name__, static_folder=None)
api = ApiHandlers()

# Serve frontend static files
_WEB_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"


@app.route("/")
def index():
    if (_WEB_DIR / "index.html").exists():
        return send_from_directory(str(_WEB_DIR), "index.html")
    return "<h2>Frontend not built. Run: cd frontend && npm run build</h2>"


@app.route("/<path:path>")
def static_files(path: str):
    return send_from_directory(str(_WEB_DIR), path)


# --- API routes ---

@app.route("/api/tools", methods=["GET"])
def get_tools():
    return jsonify(api.get_tools())


@app.route("/api/tools/scan", methods=["POST"])
def scan_tools():
    return jsonify(api.scan_tools())


@app.route("/api/tools/<tool_id>", methods=["PUT"])
def save_tool(tool_id: str):
    data = request.get_json() or {}
    data["tool_id"] = tool_id
    return jsonify(api.save_tool(data))


@app.route("/api/tools/<tool_id>/tasks", methods=["GET"])
def get_tool_tasks(tool_id: str):
    return jsonify(api.get_tool_tasks(tool_id))


@app.route("/api/tools/<tool_id>/settings", methods=["GET"])
def get_tool_settings(tool_id: str):
    return jsonify(api.get_tool_settings(tool_id))


@app.route("/api/tools/<tool_id>/settings", methods=["PUT"])
def save_tool_settings(tool_id: str):
    data = request.get_json() or {}
    return jsonify(api.save_tool_settings(tool_id, data))


@app.route("/api/schedules", methods=["GET"])
def get_schedules():
    return jsonify(api.get_schedules())


@app.route("/api/schedules", methods=["POST"])
def save_schedule():
    data = request.get_json() or {}
    return jsonify(api.save_schedule(data))


@app.route("/api/schedules/<schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id: str):
    return jsonify(api.delete_schedule(schedule_id))


@app.route("/api/run", methods=["POST"])
def run_plan():
    data = request.get_json() or {}
    return jsonify(api.run_plan(data))


@app.route("/api/stop", methods=["POST"])
def stop_run():
    return jsonify(api.stop())


@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify(api.get_status())


def main():
    """Run the dev server."""
    logger.info("Starting dev server at http://localhost:5000")
    api.start_scheduler()
    try:
        app.run(host="127.0.0.1", port=5000, debug=False)
    finally:
        api.stop_scheduler()


if __name__ == "__main__":
    main()
