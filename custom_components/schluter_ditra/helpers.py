"""Small helpers for decoding API values."""

from __future__ import annotations

from typing import Any


def temp_value(raw: Any) -> float | None:
    """Temperatures come back as {"error": null, "value": 20.5} or a bare number."""
    if isinstance(raw, dict):
        if raw.get("error"):
            return None
        return raw.get("value")
    return raw


def limit_value(raw: Any) -> float | None:
    """Limits come back as {"status": "on"|"off", "value": x}."""
    if isinstance(raw, dict):
        return raw.get("value") if raw.get("status") == "on" else None
    return raw
