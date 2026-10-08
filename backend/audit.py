"""
Append-only audit trail for the agent loop.

Every chat turn writes a record of what the agent actually did: which tools it
called, with what arguments, what came back, how the run ended, and what it
cost in tokens. Without this, an agent is a black box — you can see the reply
but not the reasoning path that produced it, which makes a wrong answer
impossible to diagnose and a spending spike impossible to attribute.

## File format

`output/audit_trail.json` is **JSON Lines**: one complete JSON object per line.

That is a deliberate choice over a single JSON array. An array has to be read,
parsed, extended and rewritten on every append — which means the whole history
is rewritten constantly, a crash mid-write can truncate the entire file, and
two concurrent writers can lose each other's records. JSON Lines appends one
line and never touches what came before, so the file is genuinely append-only
and a partial write can at worst corrupt its own last line.

Read it back with:

    [json.loads(line) for line in open(path) if line.strip()]

## Guarantees

* Opened with mode `"a"` only. Nothing in this module truncates, rewrites, or
  deletes the file, and no other module writes to it.
* A write failure never breaks a chat turn — audit logging is best-effort and
  swallows its own errors.
* Arguments and results are summarized, not stored whole, so the log cannot
  become a second copy of the catalogue.
* Message text is truncated and never includes credentials.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
AUDIT_PATH = BACKEND_DIR.parent / "output" / "audit_trail.json"

# Keep individual fields short. The audit trail is a record of control flow,
# not a data warehouse.
MAX_ARG_CHARS = 200
MAX_RESULT_CHARS = 300
MAX_MESSAGE_CHARS = 200

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_run_id() -> str:
    """Short id tying every record from one chat turn together."""
    return uuid.uuid4().hex[:12]


def _truncate(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    return value[:limit] + "...", True


def summarize(value: Any, limit: int = MAX_RESULT_CHARS) -> dict[str, Any]:
    """
    Compress a tool argument or return value into something loggable.

    Collections report their shape and a sample rather than their contents, so
    a six-product search result does not write six full product records.
    """
    if value is None:
        return {"type": "none"}

    if isinstance(value, (str, int, float, bool)):
        text, truncated = _truncate(str(value), limit)
        return {"type": type(value).__name__, "value": text, "truncated": truncated}

    # Pydantic models (every tool return type lives in models.py).
    if hasattr(value, "model_dump"):
        data = value.model_dump()
        summary: dict[str, Any] = {"type": type(value).__name__}
        for key in ("total_matches", "returned", "product_id", "id", "name", "quantity",
                    "available", "total_stock", "sold_out", "found", "signed_in",
                    "collection", "page_type", "route"):
            if key in data:
                summary[key] = data[key]
        if "results" in data and isinstance(data["results"], list):
            summary["result_ids"] = [r.get("id") for r in data["results"][:6]]
        if "note" in data and data["note"]:
            summary["note"], _ = _truncate(str(data["note"]), 120)
        return summary

    if isinstance(value, (list, tuple)):
        out: dict[str, Any] = {"type": "list", "count": len(value)}
        if value and hasattr(value[0], "model_dump"):
            first = value[0].model_dump()
            key = "collection" if "collection" in first else "category"
            out["sample"] = [
                getattr(v, key, None) for v in value[:6] if hasattr(v, key)
            ]
        return out

    if isinstance(value, dict):
        text, truncated = _truncate(json.dumps(value, default=str), limit)
        return {"type": "dict", "keys": list(value)[:10], "value": text, "truncated": truncated}

    text, truncated = _truncate(repr(value), limit)
    return {"type": type(value).__name__, "value": text, "truncated": truncated}


def write(event: str, **fields: Any) -> None:
    """
    Append one record. Never raises.

    A failure to write the audit trail must not take down a shopper's chat, so
    every error here is swallowed after one attempt.
    """
    record = {"ts": _now(), "event": event, **fields}
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, default=str, ensure_ascii=False)
        with _lock:
            # Mode "a" only — the file is never opened for writing or truncation.
            with open(AUDIT_PATH, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except Exception:  # noqa: BLE001 - auditing must never break the request
        pass


def turn_started(run_id: str, message: str, user_id: int | None, page: Any | None) -> float:
    """Record the start of a chat turn. Returns a monotonic start time."""
    text, truncated = _truncate(message, MAX_MESSAGE_CHARS)
    write(
        "turn.start",
        run_id=run_id,
        user=f"user:{user_id}" if user_id is not None else "guest",
        message=text,
        message_truncated=truncated,
        page=getattr(page, "route", None),
        page_type=getattr(page, "page_type", None),
    )
    return time.perf_counter()


def tool_called(
    run_id: str,
    tool: str,
    args: dict[str, Any],
    result: Any,
    duration_ms: float,
) -> None:
    """Record one tool call with summarized arguments and result."""
    trimmed = {k: v for k, v in args.items() if v is not None}
    args_text, args_truncated = _truncate(
        json.dumps(trimmed, default=str, ensure_ascii=False), MAX_ARG_CHARS
    )
    write(
        "tool.call",
        run_id=run_id,
        tool=tool,
        args=args_text,
        args_truncated=args_truncated,
        result=summarize(result),
        duration_ms=round(duration_ms, 1),
    )


def turn_finished(
    run_id: str,
    started: float,
    stop_reason: str,
    reply: str | None = None,
    product_ids: list[str] | None = None,
    usage: Any | None = None,
    error: str | None = None,
) -> None:
    """
    Record how a turn ended.

    `stop_reason` is the important field. One of:
      completed        - the agent produced a structured reply
      timeout          - exceeded the agent timeout
      usage_limit      - hit a request, tool-call or token ceiling
      rate_limited     - the shopper exceeded their turn budget
      content_filter   - the provider refused the input
      error            - anything else
    """
    fields: dict[str, Any] = {
        "run_id": run_id,
        "stop_reason": stop_reason,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }
    if reply is not None:
        text, truncated = _truncate(reply, MAX_MESSAGE_CHARS)
        fields["reply"] = text
        fields["reply_truncated"] = truncated
    if product_ids is not None:
        fields["product_ids"] = product_ids
        fields["products_shown"] = len(product_ids)
    if usage is not None:
        fields["usage"] = {
            "requests": getattr(usage, "requests", None),
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "tool_calls": getattr(usage, "tool_calls", None),
        }
    if error is not None:
        text, _ = _truncate(error, MAX_RESULT_CHARS)
        fields["error"] = text

    write("turn.end", **fields)


def read_all() -> list[dict[str, Any]]:
    """Parse the whole trail. For inspection and tests, not used at request time."""
    if not AUDIT_PATH.exists():
        return []
    records = []
    with open(AUDIT_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # A partially written final line is possible after a hard crash.
                continue
    return records
