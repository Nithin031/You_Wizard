"""Orchestrates the full research run: routing, execution, caching, resume,
progress tracking, cost control, and the terminal progress display.
"""
from __future__ import annotations

import asyncio
import json
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from . import answer as answer_mod
from . import contents as contents_mod
from . import research_api as research_mod
from . import search as search_mod
from .citations import dedupe_sources, rank_sources
from .questions import QUESTIONS, Question, TOPIC_ORDER, TOPIC_TITLES, questions_for_topic
from .rate_limit import Throttle
from .router import recommend_tool
from . import synthesis

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


# --------------------------------------------------------------------------
# Progress persistence (section 17: --resume)
# --------------------------------------------------------------------------
def load_progress() -> Dict[str, Any]:
    if config.PROGRESS_FILE.exists():
        try:
            return json.loads(config.PROGRESS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_progress(progress: Dict[str, Any]) -> None:
    config.PROGRESS_FILE.write_text(json.dumps(progress, indent=2, default=str), encoding="utf-8")


# --------------------------------------------------------------------------
# Cost estimation & budget enforcement (section 15)
# --------------------------------------------------------------------------
def _plan_for(questions: List[Question], enable_contents: bool) -> Dict[str, Any]:
    research_calls = 0
    search_calls = 0
    answer_calls = 0
    topics_with_questions = set()

    for q in questions:
        tool = recommend_tool(q)
        topics_with_questions.add(q.topic_slug)
        if tool == "RESEARCH":
            research_calls += 1
        elif tool == "SEARCH":
            search_calls += 1
        elif tool == "ANSWER":
            answer_calls += 1
        search_calls += len(q.search_queries)

    contents_calls = len(topics_with_questions) if enable_contents else 0
    total = (
        research_calls * config.COST_RESEARCH
        + search_calls * config.COST_SEARCH
        + answer_calls * config.COST_ANSWER
        + contents_calls * config.COST_CONTENTS
    )
    return {
        "research": research_calls,
        "search": search_calls,
        "answer": answer_calls,
        "contents": contents_calls,
        "total_cost": total,
    }


def plan_run(questions: List[Question], run_cfg) -> Dict[str, Any]:
    """Estimate cost and, if over budget, shrink the plan per section 15 rules.

    Returns a dict with the final ``questions`` list, whether ``contents``
    stays enabled, the follow-up search queries retained per question id,
    and the notes describing what (if anything) was cut.
    """
    notes: List[str] = []
    enable_contents = run_cfg.enable_contents
    active_questions = list(questions)
    followups = {q.question_id: list(q.search_queries) for q in active_questions}

    plan = _plan_for(active_questions, enable_contents)
    budget = run_cfg.budget

    if budget is not None and plan["total_cost"] > budget and enable_contents:
        enable_contents = False
        notes.append("Disabled Contents extraction to stay within budget.")
        plan = _plan_for(active_questions, enable_contents)

    if budget is not None and plan["total_cost"] > budget:
        for q in active_questions:
            if q.topic_slug in config.OPTIONAL_TOPICS and followups[q.question_id]:
                followups[q.question_id] = []
        notes.append("Dropped follow-up Search queries on optional topics to stay within budget.")
        plan = _plan_for(
            [Question(q.topic_slug, q.topic_title, q.question_id, q.text, q.tool,
                      q.research_effort, followups[q.question_id]) for q in active_questions],
            enable_contents,
        )

    if budget is not None and plan["total_cost"] > budget:
        optional_last_first = [t for t in reversed(TOPIC_ORDER) if t in config.OPTIONAL_TOPICS]
        for topic in optional_last_first:
            if plan["total_cost"] <= budget:
                break
            dropped = [q.question_id for q in active_questions if q.topic_slug == topic]
            if not dropped:
                continue
            active_questions = [q for q in active_questions if q.topic_slug != topic]
            notes.append(
                f"Skipped topic '{topic}' ({', '.join(dropped)}) to stay within budget."
            )
            plan = _plan_for(
                [Question(q.topic_slug, q.topic_title, q.question_id, q.text, q.tool,
                          q.research_effort, followups[q.question_id]) for q in active_questions],
                enable_contents,
            )

    if budget is not None and plan["total_cost"] > budget:
        notes.append(
            f"Core topics alone cost {plan['total_cost']} units, over the budget of {budget}. "
            "Proceeding with the core-topic minimum rather than silently exceeding it further "
            "cannot reduce cost below this floor without skipping required questions."
        )

    return {
        "questions": active_questions,
        "enable_contents": enable_contents,
        "followups": followups,
        "plan": plan,
        "notes": notes,
    }


# --------------------------------------------------------------------------
# Result shaping (section 7)
# --------------------------------------------------------------------------
def _extract_bullets(text: str, markers: tuple) -> List[str]:
    out = []
    for line in (text or "").splitlines():
        stripped = line.strip().lstrip("-*0123456789. ").strip()
        if not stripped:
            continue
        lowered = line.strip().lower()
        is_bullet = line.strip().startswith(("-", "*")) or (
            len(line.strip()) > 1 and line.strip()[0].isdigit()
        )
        if is_bullet and (not markers or any(m in lowered for m in markers)):
            out.append(stripped)
    return out[:8]


def build_result(question: Question, tool_used: str, answer_text: str,
                  sources: List[dict], raw_file: Optional[str]) -> Dict[str, Any]:
    key_findings = _extract_bullets(answer_text, ())
    recommendations = _extract_bullets(answer_text, ("recommend", "should use", "best"))
    implications = _extract_bullets(answer_text, ("implement", "pipeline", "feature", "design"))

    n_sources = len(sources)
    if tool_used == "RESEARCH" and n_sources >= 3:
        confidence = "high"
    elif n_sources >= 1:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "topic": question.topic_slug,
        "question_id": question.question_id,
        "question": question.text,
        "tool_used": tool_used,
        "answer": answer_text,
        "sources": rank_sources(dedupe_sources(sources)),
        "key_findings": key_findings,
        "recommendations": recommendations,
        "implementation_implications": implications,
        "confidence": confidence,
        "raw_response_file": raw_file,
    }


# --------------------------------------------------------------------------
# Per-question execution
# --------------------------------------------------------------------------
async def _execute_question(you, question: Question, followup_queries: List[str],
                             run_cfg, refresh: bool) -> Dict[str, Any]:
    tool = recommend_tool(question)
    timeout_ms = run_cfg.timeout_ms
    max_retries = run_cfg.max_retries
    use_cache = run_cfg.use_cache

    raw_blob: Dict[str, Any] = {"tool": tool, "question_id": question.question_id}
    sources: List[dict] = []
    answer_text = ""

    if tool == "RESEARCH":
        result = await research_mod.run_research(
            you, question.text, effort=question.research_effort,
            use_cache=use_cache, refresh=refresh, timeout_ms=timeout_ms, max_retries=max_retries,
        )
        answer_text = result["answer"]
        sources.extend(result["sources"])
        raw_blob["research"] = result["raw"]
    elif tool == "SEARCH":
        result = await search_mod.run_search(
            you, question.text, use_cache=use_cache, refresh=refresh,
            timeout_ms=timeout_ms, max_retries=max_retries,
        )
        sources.extend(result["sources"])
        top = sources[:5]
        answer_text = "Top sources found via Search:\n" + "\n".join(
            f"- {s['title']}: {s['url']}" for s in top
        )
        raw_blob["search"] = result["raw"]
    else:  # ANSWER (default/fallback)
        result = await answer_mod.run_answer(
            you, question.text, use_cache=use_cache, refresh=refresh,
            timeout_ms=timeout_ms, max_retries=max_retries,
        )
        answer_text = result["answer"]
        sources.extend(result["sources"])
        raw_blob["answer"] = result["raw"]

    # Section 9/11: targeted follow-up Search queries for source discovery.
    for fq in followup_queries:
        try:
            fresult = await search_mod.run_search(
                you, fq, count=5, use_cache=use_cache, refresh=refresh,
                timeout_ms=timeout_ms, max_retries=max_retries,
            )
            sources.extend(fresult["sources"])
            raw_blob.setdefault("followup_search", []).append(fresult["raw"])
        except Exception as exc:  # noqa: BLE001
            raw_blob.setdefault("followup_search_errors", []).append(
                {"query": fq, "error": str(exc)}
            )

    raw_file = None
    if run_cfg.save_raw:
        raw_path = config.RAW_DIR / f"{question.topic_slug}_{question.question_id}.json"
        raw_path.write_text(json.dumps(raw_blob, indent=2, default=str), encoding="utf-8")
        raw_file = str(raw_path.relative_to(config.PROJECT_ROOT))

    return build_result(question, tool, answer_text, sources, raw_file)


# --------------------------------------------------------------------------
# Terminal UI (section 18)
# --------------------------------------------------------------------------
def _print_start(idx: int, total: int, question: Question, tool: str) -> None:
    print(f"\n[{idx}/{total}] {question.topic_slug.upper()} {question.question_id}")
    print(f"  Tool: {tool.title()}")
    print("  Status: running...")


def _print_done(idx: int, total: int, question: Question, result: Dict[str, Any],
                 saved_path: Path) -> None:
    print(f"[{idx}/{total}] {question.topic_slug.upper()} {question.question_id}")
    print("  Status: complete")
    print(f"  Sources: {len(result['sources'])}")
    print(f"  Saved: {saved_path.relative_to(config.PROJECT_ROOT)}")


def _print_failed(idx: int, total: int, question: Question, error: Exception) -> None:
    print(f"[{idx}/{total}] {question.topic_slug.upper()} {question.question_id}")
    print("  Status: FAILED")
    print(f"  Error: {error}")


# --------------------------------------------------------------------------
# Main run
# --------------------------------------------------------------------------
async def run(run_cfg) -> Dict[str, Any]:
    from youdotcom import You  # deferred: run_research.py already checked this import

    all_questions = questions_for_topic(run_cfg.topic_filter)
    if not all_questions:
        print(f"No questions found for topic '{run_cfg.topic_filter}'.")
        return {"completed": 0, "failed": 0, "total": 0}

    planned = plan_run(all_questions, run_cfg)
    questions = planned["questions"]
    enable_contents = planned["enable_contents"]
    followups = planned["followups"]

    plan = planned["plan"]
    print("Estimated API calls:")
    print(f"  Research: {plan['research']}")
    print(f"  Search:   {plan['search']}")
    print(f"  Answer:   {plan['answer']}")
    print(f"  Contents: {plan['contents']}")
    print(f"Estimated relative cost: {plan['total_cost']} units"
          + (f" (budget: {run_cfg.budget})" if run_cfg.budget is not None else ""))
    for note in planned["notes"]:
        print(f"  NOTE: {note}")

    progress = load_progress() if run_cfg.resume else {}
    if not run_cfg.resume:
        progress = {}

    total = len(questions)
    throttle = Throttle(run_cfg.concurrency)
    topic_results: Dict[str, List[Dict[str, Any]]] = {t: [] for t in TOPIC_ORDER}
    counters = {"research": 0, "search": 0, "answer": 0, "contents": 0}
    completed = 0
    failed = 0
    lock = asyncio.Lock()

    async with You(api_key_auth=run_cfg.api_key) as you:

        async def process(idx: int, question: Question):
            nonlocal completed, failed
            qkey = f"{question.topic_slug}:{question.question_id}"

            if run_cfg.resume and progress.get(qkey, {}).get("status") == STATUS_COMPLETED:
                answer_path = config.ANSWERS_DIR / f"{question.topic_slug}_{question.question_id}.json"
                if answer_path.exists():
                    async with lock:
                        result = json.loads(answer_path.read_text(encoding="utf-8"))
                        topic_results[question.topic_slug].append(result)
                        completed += 1
                    print(f"[{idx}/{total}] {question.topic_slug.upper()} {question.question_id}"
                          " -- already completed, skipping (resume).")
                    return

            async with lock:
                progress[qkey] = {"status": STATUS_RUNNING}
                save_progress(progress)

            tool = recommend_tool(question)
            _print_start(idx, total, question, tool)

            async with throttle:
                try:
                    result = await _execute_question(
                        you, question, followups.get(question.question_id, []),
                        run_cfg, refresh=run_cfg.refresh,
                    )
                except Exception as exc:  # noqa: BLE001
                    async with lock:
                        progress[qkey] = {"status": STATUS_FAILED, "error": str(exc)}
                        save_progress(progress)
                        failed += 1
                    _print_failed(idx, total, question, exc)
                    traceback.print_exc()
                    return

            counters[tool.lower()] = counters.get(tool.lower(), 0) + 1
            counters["search"] += len(followups.get(question.question_id, []))

            answer_path = config.ANSWERS_DIR / f"{question.topic_slug}_{question.question_id}.json"
            answer_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

            async with lock:
                topic_results[question.topic_slug].append(result)
                progress[qkey] = {"status": STATUS_COMPLETED}
                save_progress(progress)
                completed += 1

            _print_done(idx, total, question, result, answer_path)

        await asyncio.gather(*(
            process(idx, q) for idx, q in enumerate(questions, start=1)
        ))

        # Section 9/11: per-topic Contents fetch of the top ranked sources.
        if enable_contents:
            for topic in TOPIC_ORDER:
                results = topic_results.get(topic) or []
                if not results:
                    continue
                all_sources = []
                for r in results:
                    all_sources.extend(r["sources"])
                top_sources = rank_sources(dedupe_sources(all_sources))[:run_cfg.max_sources_per_topic]
                urls = [s["url"] for s in top_sources if s["url"]]
                if not urls:
                    continue
                print(f"\n[Contents] Fetching {len(urls)} top sources for topic '{topic}'...")
                try:
                    pages = await contents_mod.run_contents(
                        you, urls, use_cache=run_cfg.use_cache, refresh=run_cfg.refresh,
                        timeout_ms=run_cfg.timeout_ms, max_retries=run_cfg.max_retries,
                    )
                    counters["contents"] += 1
                except Exception as exc:  # noqa: BLE001
                    print(f"  Contents fetch failed for topic '{topic}': {exc}")
                    pages = []
                sources_path = config.SOURCES_DIR / f"{topic}.json"
                sources_path.write_text(json.dumps(pages, indent=2, default=str), encoding="utf-8")
                print(f"  Saved: {sources_path.relative_to(config.PROJECT_ROOT)}")

    report_path = None
    if run_cfg.enable_synthesis:
        print("\nBuilding final synthesis report...")
        report_path = synthesis.build_report(topic_results, questions)
        print(f"Final report: {report_path.relative_to(config.PROJECT_ROOT)}")

    print("\nResearch complete.")
    topics_done = sum(1 for t in TOPIC_ORDER if topic_results.get(t))
    print(f"Topics completed: {topics_done}/{len(TOPIC_ORDER)}")
    print(f"Questions completed: {completed}/{total}")
    print(f"Research calls: {counters.get('research', 0)}")
    print(f"Search calls: {counters.get('search', 0)}")
    print(f"Contents calls: {counters.get('contents', 0)}")
    print(f"Answer calls: {counters.get('answer', 0)}")
    if report_path:
        print(f"\nFinal report:\n{report_path.relative_to(config.PROJECT_ROOT)}")

    return {"completed": completed, "failed": failed, "total": total, "report_path": report_path}
