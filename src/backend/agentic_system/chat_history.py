"""Sliding-window chat history management."""

from __future__ import annotations

from typing import Any


class SlidingWindowChatHistory:
    """Stores only the most recent messages needed for the agent context."""

    def __init__(self, window_size: int = 10) -> None:
        self.window_size = window_size
        self._messages: list[dict[str, Any]] = []

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def append(self, message: dict[str, Any]) -> None:
        self._messages.append(message)
        self._messages = self._messages[-self.window_size :]

    def extend(self, messages: list[dict[str, Any]]) -> None:
        for message in messages:
            self.append(message)
