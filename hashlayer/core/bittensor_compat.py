"""Helpers for Bittensor SDK 10.x compatibility (ExtrinsicResponse, etc.)."""

from __future__ import annotations

from typing import Any


def extrinsic_result(response: Any) -> tuple[bool, str]:
    """Normalize set_weights / extrinsic return values across SDK versions.

    Bittensor >=10 returns ``ExtrinsicResponse`` (``.success``, ``.message``).
    Older SDKs returned ``tuple[bool, str]`` or a bare bool.
    """
    if response is None:
        return False, "empty extrinsic response"

    success = getattr(response, "success", None)
    if success is not None:
        message = getattr(response, "message", None) or ""
        err = getattr(response, "error", None)
        if not success and err and not message:
            message = str(err)
        return bool(success), str(message)

    if isinstance(response, tuple):
        ok = bool(response[0]) if response else False
        msg = str(response[1]) if len(response) > 1 else ""
        return ok, msg

    return bool(response), ""
