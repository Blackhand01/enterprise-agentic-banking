"""JSON audit trail adapter for prototype traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonAuditTrail:
    """Persists lightweight audit traces in a local JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def list_events(self, limit: int = 10) -> list[dict[str, Any]]:
        events = self._read()
        return list(reversed(events[-limit:]))

    def append(self, trace: dict[str, Any]) -> None:
        events = self._read()
        events.append(trace)
        self._write(events)

    def reset(self) -> None:
        self._write([])

    def _read(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: list[dict[str, Any]]) -> None:
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
