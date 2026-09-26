"""Persistent, content-addressed cache for You.com API calls.

Every request is hashed (tool name + normalized parameters) and stored at
``output/raw/cache/<hash>.json``. Re-running the same question is free and
offline; ``--refresh`` bypasses the cache for a fresh run.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

import config


def _hash_key(tool: str, params: dict) -> str:
    payload = json.dumps({"tool": tool, "params": params}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def cache_path(tool: str, params: dict) -> Path:
    return config.CACHE_DIR / f"{_hash_key(tool, params)}.json"


def load(tool: str, params: dict) -> Optional[Any]:
    path = cache_path(tool, params)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save(tool: str, params: dict, value: Any) -> Path:
    path = cache_path(tool, params)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")
    return path
