"""Decides which You.com tool handles a given research question.

Section 6 of the spec: each question can pin a tool (RESEARCH / SEARCH /
ANSWER / CONTENTS), or leave it as "AUTO" and let this router recommend one
using the stated heuristics.
"""
from __future__ import annotations

from .questions import Question

_RESEARCH_SIGNALS = (
    "compare", "comparison", "literature", "synthesiz", "several sources",
    "multiple sources", "architecture", "benchmark", "failure mode",
    "trade-off", "tradeoff", "recommend",
)
_SEARCH_SIGNALS = (
    "find a paper", "particular paper", "github repositor", "repository",
    "documentation", "license", "write-up", "writeup", "competition",
)
_CONTENTS_SIGNALS = (
    "full paper", "full webpage", "readme", "detailed evidence from",
)


def recommend_tool(question: Question) -> str:
    """Return the tool to use for ``question`` (its pin, or a heuristic pick)."""
    if question.tool and question.tool != "AUTO":
        return question.tool

    text = question.text.lower()

    if any(sig in text for sig in _CONTENTS_SIGNALS):
        return "CONTENTS"
    if any(sig in text for sig in _SEARCH_SIGNALS):
        return "SEARCH"
    if any(sig in text for sig in _RESEARCH_SIGNALS):
        return "RESEARCH"

    # Narrow, concise, source-backed question -> ANSWER.
    return "ANSWER"
