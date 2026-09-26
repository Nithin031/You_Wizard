"""Wrapper around the You.com Research API (deep, multi-step investigation)."""
from __future__ import annotations

from typing import Any, Dict, List

from . import cache as cache_mod
from .citations import dedupe_sources, make_source
from .rate_limit import build_retry_config


async def run_research(you, query: str, *, effort: str, use_cache: bool,
                        refresh: bool, timeout_ms: int, max_retries: int) -> Dict[str, Any]:
    params = {"input": query, "research_effort": effort}

    if use_cache and not refresh:
        cached = cache_mod.load("research", params)
        if cached is not None:
            cached["_cache_hit"] = True
            return cached

    from youdotcom import models as ydc_models
    effort_enum = getattr(ydc_models.ResearchEffort, effort.upper(), ydc_models.ResearchEffort.STANDARD)

    response = await you.research_async(
        input=query,
        research_effort=effort_enum,
        background=False,
        retries=build_retry_config(max_retries),
        timeout_ms=timeout_ms,
    )
    raw = response.model_dump() if hasattr(response, "model_dump") else response
    output = raw.get("output") or {}

    sources: List[dict] = []
    for src in output.get("sources") or []:
        sources.append(make_source(
            url=src.get("url", ""),
            title=src.get("title"),
            source_type="research_source",
            relevance="; ".join(src.get("snippets") or [])[:400],
        ))

    content = output.get("content")
    answer_text = content if isinstance(content, str) else str(content)

    result = {
        "query": query,
        "answer": answer_text,
        "sources": dedupe_sources(sources),
        "warnings": raw.get("warnings") or [],
        "raw": raw,
        "_cache_hit": False,
    }
    if use_cache:
        cache_mod.save("research", params, result)
    return result
