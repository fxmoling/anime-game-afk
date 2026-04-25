"""Simple pub/sub event bus."""
from __future__ import annotations

from typing import Any, Callable

from loguru import logger as _loguru

EventHandler = Callable[..., None]


class EventBus:
    """Simple pub/sub event bus.

    Handlers are called synchronously in registration order.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def on(self, event: str, handler: EventHandler) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def off(self, event: str, handler: EventHandler) -> None:
        if event in self._handlers:
            self._handlers[event] = [
                h for h in self._handlers[event] if h is not handler
            ]

    def clear(self) -> None:
        self._handlers.clear()

    def emit(self, event: str, **kwargs: Any) -> None:
        """Call every handler registered for *event*."""
        for handler in self._handlers.get(event, []):
            try:
                handler(**kwargs)
            except Exception:
                _loguru.opt(depth=1).exception(
                    "Handler {!r} failed for event {!r}", handler, event
                )
