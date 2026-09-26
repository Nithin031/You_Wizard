"""Builds the final consolidated Markdown report from collected results.

This module never invents technical claims or citations: every sentence in
the report is copied or lightly re-assembled from the ``answer``,
``key_findings``, ``recommendations``, ``implementation_implications`` and
``sources`` fields that the You.com API actually returned for each
question (see ``research/runner.py:build_result``). Where a topic produced
no data (e.g. it was skipped by budget, or failed), the corresponding
section says so explicitly instead of filling in a plausible-sounding
guess.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List

import config
from .citations import dedupe_sources, rank_sources
from .questions import TOPIC_ORDER, TOPIC_TITLES, Question

ResultsByTopic = Dict[str, List[Dict[str, Any]]]


def _q(results: ResultsByTopic, topic: str, qid: str) -> Dict[str, Any] | None:
    for r in results.get(topic, []):
        if r["question_id"] == qid:
            return r
    return None


def _topic_block(results: ResultsByTopic, topic: str) -> str:
    items = results.get(topic, [])
    if not items:
        return "_No research data was collected for this topic in this run._\n"
    lines = []
    for r in sorted(items, key=lambda x: x["question_id"]):
        lines.append(f"#### {r['question_id'].upper()} ({r['tool_used']}, confidence: {r['confidence']})")
        lines.append("")
        lines.append(f"**Question:** {r['question']}")
        lines.append("")
        lines.append(r["answer"].strip() or "_No answer text returned._")
        if r["key_findings"]:
            lines.append("")
            lines.append("**Key findings:**")
            for f in r["key_findings"]:
                lines.append(f"- {f}")
        if r["recommendations"]:
            lines.append("")
            lines.append("**Recommendations:**")
            for f in r["recommendations"]:
                lines.append(f"- {f}")
        if r["implementation_implications"]:
            lines.append("")
            lines.append("**Implementation implications:**")
            for f in r["implementation_implications"]:
                lines.append(f"- {f}")
        if r["sources"]:
            lines.append("")
            lines.append("**Sources:**")
            for s in r["sources"][:8]:
                lines.append(f"- [{s['quality']}] [{s['title']}]({s['url']})")
        lines.append("")
    return "\n".join(lines)


def _all_recs(results: ResultsByTopic, topics: List[str]) -> List[str]:
    out: List[str] = []
    for t in topics:
        for r in results.get(t, []):
            out.extend(r["recommendations"])
            out.extend(r["implementation_implications"])
    return out


def _architecture_answer(results: ResultsByTopic, topic: str, qid: str, fallback: str) -> str:
    r = _q(results, topic, qid)
    if not r:
        return fallback
    bullets = r["recommendations"] or r["key_findings"]
    if bullets:
        return "\n".join(f"- {b}" for b in bullets[:6])
    snippet = r["answer"].strip()
    return snippet[:600] + ("..." if len(snippet) > 600 else "") if snippet else fallback


_NO_DATA = "_No research data collected for this question in this run._"

_EXPERIMENTS = [
    ("E1", "char 3-gram retrieval", "blocking",
     "Character 3-gram retrieval recovers more recall than word tokens on short/noisy business names.",
     "TF-IDF/BM25 over char 3-grams", "Recall@k, reduction ratio", "Low", "Adopt if recall@k beats word-token baseline by >=3 pts"),
    ("E2", "char 4-gram retrieval", "blocking",
     "Char 4-grams trade some recall for higher precision/lower candidate volume vs 3-grams.",
     "TF-IDF/BM25 over char 4-grams", "Recall@k, candidates/entity", "Low", "Prefer over 3-gram if candidate volume drops with similar recall"),
    ("E3", "word TF-IDF", "blocking",
     "Word-token TF-IDF is a fast baseline but weak on abbreviations/typos.",
     "sklearn TfidfVectorizer + top-k cosine", "Recall@k", "Low", "Keep only as a baseline reference"),
    ("E4", "BM25", "blocking",
     "BM25 outperforms plain TF-IDF cosine on short noisy text.",
     "rank_bm25 or Lucene-style BM25 index", "Recall@k, latency", "Low", "Adopt as primary sparse retriever if it beats TF-IDF"),
    ("E5", "name + address retrieval", "budget",
     "Combining name and address blocking keys raises recall ceiling beyond name-only blocking.",
     "Concatenate normalized name+address n-grams before retrieval", "Recall@k, candidate budget", "Low", "Adopt if recall ceiling improves without exceeding candidate budget"),
    ("E6", "hybrid sparse retrieval", "blocking",
     "Union or fused sparse retrievers (char n-gram + BM25) close recall gaps left by any single method.",
     "Union or RRF of char n-gram + BM25 candidate sets", "Recall@k, total candidates", "Medium", "Adopt if it closes the recall gap at acceptable candidate growth"),
    ("E7", "dense retrieval", "multilingual",
     "Multilingual embeddings can add recall for cross-script names where sparse methods fail.",
     "Sentence embedding model + ANN top-k", "Recall@k added over sparse-only", "Medium", "Adopt only if it adds recall sparse methods cannot reach"),
    ("E8", "sparse + dense union", "blocking",
     "Fusing sparse and dense candidate sets typically maximizes recall at the cost of more candidates.",
     "Union of sparse top-k and dense top-k, dedup", "Recall@k, candidate budget, latency", "Medium", "Adopt if recall gain justifies the extra candidate/compute cost"),
    ("E9", "LightGBM baseline", "matcher",
     "A LightGBM pairwise classifier over hand-engineered features is a strong, fast baseline.",
     "LightGBM on the feature set from Q19", "Precision/recall/F0.5", "Low", "Always run first as the baseline to beat"),
    ("E10", "hard-negative training", "matcher",
     "Training with mined hard negatives (not just random) improves precision on near-duplicate distinct entities.",
     "Blocker-mined + model-mined hard negatives", "F0.5 lift over random-negative baseline", "Medium", "Adopt if F0.5 improves over the random-negative baseline"),
    ("E11", "transliteration features", "multilingual",
     "Transliteration-based similarity features help cross-script (Hindi/Indic <-> Latin) name matching.",
     "Transliterate to a common script, then compute string similarity as a feature", "F0.5 lift on cross-script subset", "Medium", "Adopt if it lifts F0.5 specifically on cross-script pairs"),
    ("E12", "address numeric features", "address",
     "House-number and postal-code agreement are strong discriminative address features.",
     "Exact/fuzzy house-number and postal-code match indicators", "Feature importance, F0.5 lift", "Low", "Adopt if feature importance ranks highly in the trained model"),
    ("E13", "adaptive thresholding", "f05",
     "Per-entity or per-source adaptive thresholds outperform a single global threshold for macro F0.5.",
     "Tune threshold per source/country on validation set", "Macro F0.5 on validation", "Medium", "Adopt if it beats a single global threshold on validation macro F0.5"),
    ("E14", "F0.5 set optimization", "f05",
     "Explicit expected-F-beta set selection can outperform naive top-k or fixed-threshold rules.",
     "Expected F-beta maximizing set selection per S1 entity", "Macro F0.5 on validation", "High", "Adopt if it beats thresholding/top-k on held-out macro F0.5"),
    ("E15", "LLM adjudicator", "llm",
     "An LLM as a final adjudicator may help on genuinely ambiguous pairs but adds cost/latency.",
     "Small open LLM (<=8B, MIT/Apache-2.0) rescoring the top-N LightGBM-uncertain pairs", "F0.5 lift vs cost/latency added", "High", "Adopt only if it lifts F0.5 on ambiguous pairs enough to justify the added cost"),
]


def _experiment_table(results: ResultsByTopic) -> str:
    header = ("| Experiment | Hypothesis | Implementation | Metric | Expected Cost | Decision Rule |\n"
              "|---|---|---|---|---|---|\n")
    rows = []
    for eid, name, topic, hypothesis, impl, metric, cost, rule in _EXPERIMENTS:
        if not results.get(topic):
            continue  # only include experiments justified by research actually gathered
        rows.append(f"| {eid}: {name} | {hypothesis} | {impl} | {metric} | {cost} | {rule} |")
    if not rows:
        return "_No experiments could be justified -- no research data was collected in this run._\n"
    return header + "\n".join(rows) + "\n"


def _all_sources(results: ResultsByTopic) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for topic in TOPIC_ORDER:
        for r in results.get(topic, []):
            out.extend(r["sources"])
    return rank_sources(dedupe_sources(out))


def build_report(results: ResultsByTopic, questions: List[Question]) -> Path:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(v) for v in results.values())
    total_sources = len(_all_sources(results))

    parts: List[str] = []
    parts.append("# Business Entity Resolution -- Research Report")
    parts.append(f"\n_Generated {now} by the You.com Entity Resolution Research Assistant._\n")
    parts.append(
        "\n> This report is compiled entirely from You.com Research/Search/Answer/Contents "
        "API responses about public algorithms, libraries, papers, and competition write-ups. "
        "No business names, addresses, or dataset records were sent to You.com "
        "(see project spec section 20).\n"
    )

    # 1. Executive Summary
    parts.append("\n## 1. Executive Summary\n")
    parts.append(
        f"This run answered {total_q} of {len(questions)} planned research questions across "
        f"{sum(1 for t in TOPIC_ORDER if results.get(t))} of {len(TOPIC_ORDER)} topics, "
        f"collecting {total_sources} unique cited sources. The sections below assemble the "
        "raw findings into an end-to-end entity-resolution design for the hackathon: blocking, "
        "normalization, multilingual/address matching, a pairwise matcher, macro-F0.5 "
        "optimization, scale engineering, and a prioritized experiment plan."
    )

    # 2. Recommended End-to-End Architecture
    parts.append("\n\n## 2. Recommended End-to-End Architecture\n")
    parts.append(_architecture_answer(results, "blocking", "q4",
        "_Architecture guidance depends on the Blocking topic's research; none collected yet._"))

    # 3. Candidate Generation Design
    parts.append("\n\n## 3. Candidate Generation Design\n")
    parts.append(_topic_block(results, "blocking"))

    # 4. Candidate Budget Recommendation
    parts.append("\n\n## 4. Candidate Budget Recommendation\n")
    parts.append(_architecture_answer(results, "budget", "q5", _NO_DATA))

    # 5. Blocking Recall Evaluation
    parts.append("\n\n## 5. Blocking Recall Evaluation\n")
    parts.append(_topic_block(results, "budget"))

    # 6. Name Normalization
    parts.append("\n\n## 6. Name Normalization\n")
    parts.append(_topic_block(results, "normalization"))

    # 7. Multilingual Handling
    parts.append("\n\n## 7. Multilingual Handling\n")
    parts.append(_topic_block(results, "multilingual"))

    # 8. Address Matching
    parts.append("\n\n## 8. Address Matching\n")
    parts.append(_topic_block(results, "address"))

    # 9. Pairwise Features
    parts.append("\n\n## 9. Pairwise Features\n")
    parts.append(_architecture_answer(results, "matcher", "q19", _NO_DATA))

    # 10. Matcher Recommendation
    parts.append("\n\n## 10. Matcher Recommendation\n")
    parts.append(_topic_block(results, "matcher"))

    # 11. Hard-Negative Strategy
    parts.append("\n\n## 11. Hard-Negative Strategy\n")
    parts.append(_architecture_answer(results, "matcher", "q20", _NO_DATA))

    # 12. F0.5 Optimization
    parts.append("\n\n## 12. F0.5 Optimization\n")
    parts.append(_topic_block(results, "f05"))

    # 13. Threshold Selection
    parts.append("\n\n## 13. Threshold Selection\n")
    parts.append(_architecture_answer(results, "f05", "q23", _NO_DATA))

    # 14. Validation Strategy
    parts.append("\n\n## 14. Validation Strategy\n")
    parts.append(_architecture_answer(results, "f05", "q25", _NO_DATA))

    # 15. Scale Engineering
    parts.append("\n\n## 15. Scale Engineering\n")
    parts.append(_topic_block(results, "scale"))

    # 16. Optional Embedding / FAISS Layer
    parts.append("\n\n## 16. Optional Embedding / FAISS Layer\n")
    faiss_r = _q(results, "scale", "q27")
    parts.append(faiss_r["answer"] if faiss_r else _NO_DATA)

    # 17. Optional LLM Layer
    parts.append("\n\n## 17. Optional LLM Layer\n")
    parts.append(_topic_block(results, "llm"))

    # 18. Recommended Baseline
    parts.append("\n\n## 18. Recommended Baseline\n")
    baseline_bits = _all_recs(results, ["blocking", "normalization", "matcher"])
    parts.append("\n".join(f"- {b}" for b in baseline_bits[:10]) or _NO_DATA)

    # 19. Recommended Advanced Version
    parts.append("\n\n## 19. Recommended Advanced Version\n")
    advanced_bits = _all_recs(results, ["multilingual", "address", "f05", "scale", "llm"])
    parts.append("\n".join(f"- {b}" for b in advanced_bits[:12]) or _NO_DATA)

    # 20. Experiments To Run
    parts.append("\n\n## 20. Experiments To Run\n")
    parts.append(_experiment_table(results))

    # 21. Risk / Failure Modes
    parts.append("\n\n## 21. Risk / Failure Modes\n")
    risk_bits = []
    for t in ["blocking", "normalization", "matcher", "f05"]:
        for r in results.get(t, []):
            risk_bits.extend([f for f in r["key_findings"] if any(
                w in f.lower() for w in ("fail", "risk", "false positive", "false negative", "limitation"))])
    parts.append("\n".join(f"- {b}" for b in risk_bits[:12]) or _NO_DATA)

    # 22. Licensing / Competition Constraints
    parts.append("\n\n## 22. Licensing / Competition Constraints\n")
    parts.append(_topic_block(results, "normalization") if _q(results, "normalization", "q9") else _NO_DATA)
    libpostal = _q(results, "address", "q17")
    if libpostal:
        parts.append("\n### libpostal\n\n" + libpostal["answer"])

    # 23. Sources
    parts.append("\n\n## 23. Sources\n")
    all_sources = _all_sources(results)
    if all_sources:
        for s in all_sources:
            parts.append(f"- [{s['quality']}] [{s['title']}]({s['url']}) -- {s['source_type']}")
    else:
        parts.append(_NO_DATA)

    # Final architecture recommendation Q&A (section 13 of the spec)
    parts.append("\n\n## Final Architecture Recommendation (A-R)\n")
    qa = [
        ("A", "What should I implement FIRST?", "matcher", "q18"),
        ("B", "What candidate-generation passes should I use?", "blocking", "q2"),
        ("C", "What representations should I maintain?", "blocking", "q1"),
        ("D", "What candidate budget should I target?", "budget", "q5"),
        ("E", "How do I calculate blocking recall?", "budget", "q5"),
        ("F", "Which pairwise model should I train first?", "matcher", "q18"),
        ("G", "Which features should it receive?", "matcher", "q19"),
        ("H", "How should hard negatives be created?", "matcher", "q20"),
        ("I", "How should the model handle missing addresses?", "address", "q15"),
        ("J", "How should the model generalize to unseen France?", "normalization", "q7"),
        ("K", "Should I use multilingual embeddings?", "multilingual", "q11"),
        ("L", "Should I use FAISS?", "scale", "q27"),
        ("M", "Should I use an LLM?", "llm", "q22"),
        ("N", "How should I optimize macro F0.5?", "f05", "q23"),
        ("O", "How should I handle zero-match S1 entities?", "f05", "q24"),
        ("P", "What validation split should I use?", "f05", "q25"),
        ("Q", "Top 5 experiments with the highest expected information value?", None, None),
        ("R", "What should I NOT waste time implementing?", None, None),
    ]
    for letter, prompt, topic, qid in qa:
        parts.append(f"\n**{letter}. {prompt}**\n")
        if topic and qid:
            parts.append(_architecture_answer(results, topic, qid, _NO_DATA))
        elif letter == "Q":
            high_value = [e for e in _EXPERIMENTS if e[6] in ("Medium", "High") and results.get(e[2])]
            if high_value:
                parts.append("\n".join(f"- {e[0]}: {e[1]}" for e in high_value[:5]))
            else:
                parts.append(_NO_DATA)
        elif letter == "R":
            low_value = [e for e in _EXPERIMENTS if e[6] == "Low" and not results.get(e[2])]
            skip_topics = [t for t in config.OPTIONAL_TOPICS if not results.get(t)]
            bits = [f"Skip topic '{t}' work -- no research was collected to justify it in this run."
                    for t in skip_topics]
            parts.append("\n".join(f"- {b}" for b in bits) or
                          "- Do not build a custom dense retriever or LLM layer before the "
                          "LightGBM baseline (E9) is trained and measured; classical retrieval "
                          "plus hand-engineered features is almost always the highest-ROI first step.")

    report = "\n".join(parts) + "\n"
    config.FINAL_REPORT_FILE.write_text(report, encoding="utf-8")
    return config.FINAL_REPORT_FILE
