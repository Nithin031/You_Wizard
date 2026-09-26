"""Wrapper around the You.com Answer API (focused, cited answers)."""
from __future__ import annotations

from typing import Any, Dict, List

from . import cache as cache_mod
from .citations import dedupe_sources, make_source
from .rate_limit import build_retry_config


async def run_answer(you, query: str, *, use_cache: bool, refresh: bool,
                      timeout_ms: int, max_retries: int) -> Dict[str, Any]:
    params = {"query": query}

    if use_cache and not refresh:
        cached = cache_mod.load("answer", params)
        if cached is not None:
            cached["_cache_hit"] = True
            return cached

    response = await you.answer_async(
        query=query,
        retries=build_retry_config(max_retries),
        timeout_ms=timeout_ms,
    )
    raw = response.model_dump() if hasattr(response, "model_dump") else response

    sources: List[dict] = []
    for citation in raw.get("citations") or []:
        excerpts = citation.get("excerpts") or []
        sources.append(make_source(
            url=citation.get("source", ""),
            source_type="answer_citation",
            relevance=" ".join(excerpts)[:400],
        ))

    result = {
        "query": query,
        "answer": raw.get("answer", ""),
        "sources": dedupe_sources(sources),
        "raw": raw,
        "_cache_hit": False,
    }
    if use_cache:
        cache_mod.save("answer", params, result)
    return result
