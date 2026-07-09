"""Shared audit trace metric helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


SUCCESSFUL_TOOL_STATUSES = {
    "EXECUTED",
    "BLOCKED",
    "DUPLICATE",
    "EVENT_PROCESSED",
    "RECORDED",
}


def audit_metrics(
    *,
    latency_ms: int,
    tool_calls: int,
    tool_result_status: str,
    trace_id: str,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "latency_ms": latency_ms,
        "tokens_estimated": 0,
        "tool_calls": tool_calls,
        "tool_failures": 0 if tool_result_status in SUCCESSFUL_TOOL_STATUSES else 1,
        "timed_out": False,
    }


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
