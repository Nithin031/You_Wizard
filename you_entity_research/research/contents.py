"""Wrapper around the You.com Contents API (full-page extraction)."""
from __future__ import annotations

from typing import Any, Dict, List

from . import cache as cache_mod
from .rate_limit import build_retry_config


async def run_contents(you, urls: List[str], *, use_cache: bool, refresh: bool,
                        timeout_ms: int, max_retries: int) -> List[Dict[str, Any]]:
    urls = [u for u in urls if u]
    if not urls:
        return []
    params = {"urls": sorted(urls)}

    if use_cache and not refresh:
        cached = cache_mod.load("contents", params)
        if cached is not None:
            return cached

    try:
        from youdotcom import models as ydc_models
        formats = [ydc_models.ContentsFormats.MARKDOWN]
    except ImportError:
        formats = None

    try:
        pages = await you.contents_async(
            urls=urls,
            formats=formats,
            retries=build_retry_config(max_retries),
            timeout_ms=timeout_ms,
        )
    except Exception as exc:  # noqa: BLE001 - one bad URL must not sink the topic
        return [{"url": u, "error": str(exc)} for u in urls]

    out: List[Dict[str, Any]] = []
    for page in pages:
        raw = page.model_dump() if hasattr(page, "model_dump") else page
        out.append({
            "url": raw.get("url", ""),
            "title": raw.get("title"),
            "markdown": raw.get("markdown"),
            "html_present": bool(raw.get("html")),
        })

    if use_cache:
        cache_mod.save("contents", params, out)
    return out
