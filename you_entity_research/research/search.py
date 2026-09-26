"""Wrapper around the You.com Search API (targeted source discovery)."""
from __future__ import annotations

from typing import Any, Dict, List

from . import cache as cache_mod
from .citations import dedupe_sources, make_source
from .rate_limit import build_retry_config


async def run_search(you, query: str, *, count: int = 10, use_cache: bool,
                      refresh: bool, timeout_ms: int, max_retries: int) -> Dict[str, Any]:
    params = {"query": query, "count": count}

    if use_cache and not refresh:
        cached = cache_mod.load("search", params)
        if cached is not None:
            cached["_cache_hit"] = True
            return cached

    response = await you.search_async(
        query=query,
        count=count,
        retries=build_retry_config(max_retries),
        timeout_ms=timeout_ms,
    )
    raw = response.model_dump() if hasattr(response, "model_dump") else response
    sources: List[dict] = []
    web_results = (raw.get("results") or {}).get("web") or []
    for item in web_results:
        sources.append(make_source(
            url=item.get("url", ""),
            title=item.get("title"),
            source_type="web_search_result",
            relevance="; ".join(item.get("snippets") or [])[:400],
        ))
    news_results = (raw.get("results") or {}).get("news") or []
    for item in news_results:
        sources.append(make_source(
            url=item.get("url", ""),
            title=item.get("title"),
            source_type="news_search_result",
            relevance=(item.get("description") or "")[:400],
        ))

    result = {
        "query": query,
        "sources": dedupe_sources(sources),
        "raw": raw,
        "_cache_hit": False,
    }
    if use_cache:
        cache_mod.save("search", params, result)
    return result
