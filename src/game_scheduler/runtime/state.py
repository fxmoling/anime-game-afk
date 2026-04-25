"""Persistent state store backed by JSON."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from loguru import logger as _loguru


class StateStore:
    """Simple persistent key-value store backed by a JSON file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._data: dict[str, Any] = {}
        if self._path.exists():
            self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._data

    @property
    def keys(self) -> list[str]:
        return list(self._data.keys())

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._save()

    def clear(self) -> None:
        self._data.clear()
        self._save()

    def _load(self) -> None:
        try:
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, ValueError) as exc:
            _loguru.warning(
                "Corrupt state file {}, backing up and starting fresh: {}",
                self._path, exc,
            )
            backup = self._path.with_suffix(".json.corrupt")
            try:
                shutil.copy2(self._path, backup)
            except OSError:
                pass
            self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self._path)
