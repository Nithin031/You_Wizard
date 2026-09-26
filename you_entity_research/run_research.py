#!/usr/bin/env python3
"""You.com Entity Resolution Research Assistant -- single entry point.

    export YDC_API_KEY="YOUR_API_KEY"      # Linux/macOS
    $env:YDC_API_KEY="YOUR_API_KEY"        # Windows PowerShell
    python run_research.py

See README.md for the full command reference.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import config


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_research.py",
        description="Automated You.com research assistant for the Business Entity "
                    "Resolution hackathon.",
    )
    p.add_argument("--concurrency", type=int, default=config.DEFAULT_CONCURRENCY,
                   help=f"Max concurrent API calls (default: {config.DEFAULT_CONCURRENCY})")
    p.add_argument("--timeout", type=int, default=config.DEFAULT_TIMEOUT,
                   help=f"Per-request timeout in seconds (default: {config.DEFAULT_TIMEOUT})")
    p.add_argument("--max-retries", type=int, default=config.MAX_RETRIES,
                   help=f"Max retries per request (default: {config.MAX_RETRIES})")
    p.add_argument("--no-contents", action="store_true",
                   help="Disable the Contents API follow-up fetch stage.")
    p.add_argument("--no-synthesis", action="store_true",
                   help="Skip building the final consolidated Markdown report.")
    p.add_argument("--no-cache", action="store_true",
                   help="Disable the on-disk response cache entirely.")
    p.add_argument("--topic", type=str, default=None,
                   help="Only run questions for this topic slug (see --list-topics).")
    p.add_argument("--list-topics", action="store_true",
                   help="List available topic slugs and exit (no API key needed).")
    p.add_argument("--resume", action="store_true",
                   help="Resume from output/progress.json, skipping completed questions.")
    p.add_argument("--refresh", action="store_true",
                   help="Ignore the cache and force fresh API calls.")
    p.add_argument("--budget", type=int, default=None,
                   help="Hard ceiling on estimated relative API cost (see README).")
    p.add_argument("--max-sources-per-topic", type=int, default=config.MAX_SOURCES_PER_TOPIC,
                   help=f"Max sources fetched via Contents per topic "
                        f"(default: {config.MAX_SOURCES_PER_TOPIC})")
    return p.parse_args(argv)


def check_sdk_installed() -> bool:
    try:
        import youdotcom  # noqa: F401
        return True
    except ImportError:
        print(
            "ERROR: the official You.com SDK is not installed.\n\n"
            "Install it with:\n"
            "    pip install -r requirements.txt\n"
            "or:\n"
            "    pip install youdotcom\n",
            file=sys.stderr,
        )
        return False


def check_api_key() -> str | None:
    key = config.resolve_api_key()
    if not key:
        print(
            "ERROR: YDC_API_KEY is not set.\n\n"
            "Set your You.com API key before running this tool:\n\n"
            "  Linux/macOS:\n"
            '    export YDC_API_KEY="YOUR_API_KEY"\n\n'
            "  Windows PowerShell:\n"
            '    $env:YDC_API_KEY="YOUR_API_KEY"\n\n'
            "Or copy .env.example to .env in this directory and fill in your key:\n"
            f"    {config.PROJECT_ROOT / '.env.example'}\n"
            f"    -> {config.PROJECT_ROOT / '.env'}\n",
            file=sys.stderr,
        )
        return None
    return key


def main(argv=None) -> int:
    args = parse_args(argv)

    from research.questions import list_topics  # local import: no SDK needed for --list-topics

    if args.list_topics:
        print("Available topics:\n")
        for line in list_topics():
            print(f"  {line}")
        return 0

    if not check_sdk_installed():
        return 1

    api_key = check_api_key()
    if not api_key:
        return 1

    run_cfg = config.RunConfig(
        concurrency=args.concurrency,
        timeout_s=args.timeout,
        max_retries=args.max_retries,
        enable_contents=not args.no_contents,
        enable_synthesis=not args.no_synthesis,
        save_raw=config.SAVE_RAW_RESPONSES,
        use_cache=not args.no_cache,
        max_sources_per_topic=args.max_sources_per_topic,
        topic_filter=args.topic,
        resume=args.resume,
        refresh=args.refresh,
        budget=args.budget,
        api_key=api_key,
    )

    from research import runner  # deferred: imports youdotcom, checked above

    print("You.com Entity Resolution Research Assistant")
    print("=" * 60)
    print(f"Concurrency: {run_cfg.concurrency}  Timeout: {run_cfg.timeout_s}s  "
          f"Cache: {'on' if run_cfg.use_cache else 'off'}  "
          f"Contents: {'on' if run_cfg.enable_contents else 'off'}")
    if run_cfg.topic_filter:
        print(f"Topic filter: {run_cfg.topic_filter}")
    if run_cfg.resume:
        print("Mode: resume")
    print("=" * 60)

    summary = asyncio.run(runner.run(run_cfg))
    return 0 if summary.get("failed", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
