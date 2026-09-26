"""Normalizes citations/sources from any You.com tool into one shared shape.

Every question's result carries a ``sources`` list of:

    {"title": ..., "url": ..., "source_type": ..., "relevance": ..., "quality": ...}

``quality`` follows section 10 of the spec: A = primary paper / official
documentation / official repository / benchmark; B = reputable technical
article / competition write-up; C = secondary article/blog; D =
low-confidence source. We never invent a citation: every entry here is
copied from a field the You.com API actually returned.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

_A_DOMAINS = (
    "arxiv.org", "dl.acm.org", "vldb.org", "aclanthology.org",
    "openreview.net", "github.com", "pypi.org", "readthedocs.io",
    "docs.you.com", "sigmod.org", "ieee.org", "usenix.org",
    "kaggle.com/competitions",
)
_B_DOMAINS = (
    "medium.com", "towardsdatascience.com", "engineering.", "tech.",
    "eng.", "kaggle.com/code", "kaggle.com/discussions",
)


def classify_quality(url: str) -> str:
    if not url:
        return "D"
    host_path = url.lower()
    if any(dom in host_path for dom in _A_DOMAINS):
        return "A"
    if any(dom in host_path for dom in _B_DOMAINS):
        return "B"
    try:
        host = urlparse(url).netloc
    except ValueError:
        host = ""
    if host.endswith((".gov", ".edu")):
        return "A"
    if host.count(".") <= 1 and not host.startswith("www.blog"):
        return "C"
    return "D"


def _clean_title(title: Optional[str], url: str) -> str:
    if title and title.strip():
        return title.strip()
    parsed = urlparse(url)
    return parsed.netloc or url


def make_source(
    *,
    url: str,
    title: Optional[str] = None,
    source_type: str = "web",
    relevance: str = "",
) -> Dict[str, Any]:
    url = (url or "").strip()
    return {
        "title": _clean_title(title, url),
        "url": url,
        "source_type": source_type,
        "relevance": relevance,
        "quality": classify_quality(url),
    }


def dedupe_sources(sources: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for src in sources:
        url = re.sub(r"[#?].*$", "", (src.get("url") or "").rstrip("/"))
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(src)
    return out


def rank_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = {"A": 0, "B": 1, "C": 2, "D": 3}
    return sorted(sources, key=lambda s: order.get(s.get("quality", "D"), 3))
