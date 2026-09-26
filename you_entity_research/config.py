"""Central configuration for the You.com Entity Resolution Research Assistant.

All defaults live here so the user can tune behavior without touching the
rest of the codebase. Every value can also be overridden from the command
line (see ``run_research.py --help``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
RAW_DIR = OUTPUT_DIR / "raw"
CACHE_DIR = RAW_DIR / "cache"
SOURCES_DIR = OUTPUT_DIR / "sources"
ANSWERS_DIR = OUTPUT_DIR / "answers"
FINAL_DIR = OUTPUT_DIR / "final"
LOGS_DIR = PROJECT_ROOT / "logs"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"
FINAL_REPORT_FILE = FINAL_DIR / "entity_resolution_research_report.md"

for _d in (OUTPUT_DIR, RAW_DIR, CACHE_DIR, SOURCES_DIR, ANSWERS_DIR, FINAL_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Tunable defaults (section 5 of the spec)
# --------------------------------------------------------------------------
DEFAULT_CONCURRENCY = 3
DEFAULT_TIMEOUT = 180  # seconds
MAX_RETRIES = 4
ENABLE_CONTENT_EXTRACTION = True
ENABLE_FINAL_SYNTHESIS = True
SAVE_RAW_RESPONSES = True
USE_CACHE = True
MAX_SOURCES_PER_TOPIC = 5
MAX_RESEARCH_ROUNDS_PER_TOPIC = 2

# Relative "cost units" used for --budget accounting. These are not real
# dollar costs -- they are a simple, configurable proxy so the tool can
# reason about which optional calls to drop when a budget is set.
COST_RESEARCH = 5
COST_SEARCH = 1
COST_ANSWER = 2
COST_CONTENTS = 1

# Topics considered "core" for the hackathon deliverable. When a --budget
# forces cuts, priority-2 (non-core) topics lose their optional follow-up
# calls first, then their questions are skipped entirely if still over
# budget -- core topics are always executed last to be cut.
CORE_TOPICS = {
    "blocking",
    "budget",
    "normalization",
    "address",
    "matcher",
    "f05",
}
OPTIONAL_TOPICS = {
    "multilingual",
    "llm",
    "scale",
    "competition",
}

REQUEST_TIMEOUT_MS = DEFAULT_TIMEOUT * 1000


@dataclass
class RunConfig:
    """Runtime configuration, built from defaults + CLI overrides."""

    concurrency: int = DEFAULT_CONCURRENCY
    timeout_s: int = DEFAULT_TIMEOUT
    max_retries: int = MAX_RETRIES
    enable_contents: bool = ENABLE_CONTENT_EXTRACTION
    enable_synthesis: bool = ENABLE_FINAL_SYNTHESIS
    save_raw: bool = SAVE_RAW_RESPONSES
    use_cache: bool = USE_CACHE
    max_sources_per_topic: int = MAX_SOURCES_PER_TOPIC
    max_research_rounds: int = MAX_RESEARCH_ROUNDS_PER_TOPIC
    topic_filter: Optional[str] = None
    resume: bool = False
    refresh: bool = False
    list_topics: bool = False
    budget: Optional[int] = None
    api_key: Optional[str] = field(default=None, repr=False)

    @property
    def timeout_ms(self) -> int:
        return self.timeout_s * 1000


def resolve_api_key() -> Optional[str]:
    """Resolve YDC_API_KEY from the environment, loading a local .env if present.

    Only ``YDC_API_KEY`` is consulted, matching the official SDK's own
    environment lookup so behavior stays identical whether the key is
    passed explicitly or left for the SDK to discover.
    """
    key = os.environ.get("YDC_API_KEY")
    if key and key.strip():
        return key.strip()

    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name == "YDC_API_KEY" and value:
                os.environ.setdefault("YDC_API_KEY", value)
                return value
    return None
