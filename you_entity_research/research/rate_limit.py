"""Concurrency control and retry/backoff configuration for You.com calls.

The official SDK already retries 429/500/502/503/504 with exponential
backoff and honors ``Retry-After`` when we hand it a ``RetryConfig`` (see
``youdotcom.utils.retries``). This module builds that config from
``config.py`` and layers an ``asyncio.Semaphore`` on top so we never exceed
the user-configured concurrency limit, independent of what any single
request's retries are doing.
"""
from __future__ import annotations

import asyncio
from typing import Optional

try:
    from youdotcom import utils as ydc_utils
except ImportError:  # pragma: no cover - surfaced clearly by run_research.py
    ydc_utils = None  # type: ignore[assignment]


def build_retry_config(max_retries: int):
    """Build a ``youdotcom.utils.RetryConfig`` with exponential backoff."""
    if ydc_utils is None:
        return None
    backoff = ydc_utils.BackoffStrategy(
        initial_interval=500,       # ms
        max_interval=20_000,        # ms
        exponent=2.0,
        max_elapsed_time=max_retries * 25_000,
        jitter_ms=500,
    )
    return ydc_utils.RetryConfig(
        strategy="backoff",
        backoff=backoff,
        retry_connection_errors=True,
    )


class Throttle:
    """Wraps an ``asyncio.Semaphore`` sized to the configured concurrency."""

    def __init__(self, concurrency: int):
        self._sem = asyncio.Semaphore(max(1, concurrency))

    async def __aenter__(self):
        await self._sem.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._sem.release()
        return False
