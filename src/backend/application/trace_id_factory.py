"""Trace ID helpers for auditability."""

from __future__ import annotations

import time


def new_trace_id() -> str:
    return f"trc_{int(time.time() * 1000):x}"
