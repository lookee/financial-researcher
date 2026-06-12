"""Retry helper for transient network failures (stdlib only)."""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable
from typing import TypeVar

import requests

T = TypeVar("T")

_RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})

_TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    requests.ConnectionError,
    requests.Timeout,
    ConnectionError,
    TimeoutError,
    OSError,
    json.JSONDecodeError,
)


def is_retryable(exc: BaseException) -> bool:
    """Return True for transient HTTP/network failures worth retrying."""
    if isinstance(exc, requests.HTTPError):
        response = exc.response
        if response is not None:
            return response.status_code in _RETRYABLE_HTTP_STATUS
        return False
    return isinstance(exc, _TRANSIENT_EXCEPTIONS)


def with_retries(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
) -> T:
    """Call ``fn`` with exponential backoff on transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc) or attempt >= attempts - 1:
                raise
            last_exc = exc
            delay = base_delay * (2**attempt) + random.uniform(0, 0.25)
            time.sleep(delay)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("with_retries exhausted without result")
