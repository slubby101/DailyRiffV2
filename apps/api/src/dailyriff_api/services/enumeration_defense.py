"""Enumeration defense — constant-time response utility.

Ensures endpoints like password-reset always take the same minimum time,
preventing timing-based user enumeration attacks.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

DEFAULT_MIN_DURATION = 0.2


async def constant_time_response(
    operation: Callable[[], Awaitable[Any]],
    *,
    min_duration: float = DEFAULT_MIN_DURATION,
) -> Any:
    start = time.monotonic()
    exc: BaseException | None = None
    result: Any = None

    try:
        result = await operation()
    except Exception as e:
        exc = e

    elapsed = time.monotonic() - start
    remaining = min_duration - elapsed
    if remaining > 0:
        await asyncio.sleep(remaining)

    if exc is not None:
        raise exc
    return result
