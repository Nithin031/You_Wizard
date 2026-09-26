"""The 30 research questions for the Business Entity Resolution hackathon.

Each :class:`Question` is a purely local data record -- no business data,
no dataset records, nothing proprietary. Only algorithm/library/benchmark
research questions are sent to You.com (see the competition restriction in
``README.md`` section 9 / project spec section 20).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

Tool = str  # one of "RESEARCH", "SEARCH", "ANSWER", "AUTO"


@dataclass(frozen=True)
class Question:
    topic_slug: str
    topic_title: str
    question_id: str
    text: str
    tool: Tool = "AUTO"
    research_effort: str = "standard"
    search_queries: List[str] = field(default_factory=list)


QUESTIONS: List[Question] = [
    # ------------------------------------------------------------------
    # TOPIC 1: BLOCKING / CANDIDATE GENERATION
    # ------------------------------------------------------------------
    Question(
        "blocking", "Blocking / Candidate Generation", "q1",
        "For entity matching with 1-10 million records per side, compare top-k "
        "TF-IDF, BM25, MinHash-LSH, and dense retrieval blockers on recall at "
        "k = 10, 50, and 100. Focus on noisy business names and addresses. "
        "Compare word tokens, character 3-grams, and character 4-grams. Report "
        "published recall numbers, computational cost, memory usage, and "
        "failure modes.",
        tool="RESEARCH", research_effort="deep",
        search_queries=["site:vldb.org blocking entity matching"],
    ),
    Question(
        "blocking", "Blocking / Candidate Generation", "q2",
        "How should hybrid sparse+dense candidate generation be designed for "
        "large-scale entity resolution? Compare union, weighted score fusion, "
        "reciprocal rank fusion, and learned reranking. Quantify when dense "
        "retrieval adds recall beyond character n-gram or BM25 retrieval for "
        "short noisy business names.",
        tool="RESEARCH", research_effort="standard",
        search_queries=["reciprocal rank fusion entity blocking"],
    ),
    Question(
        "blocking", "Blocking / Candidate Generation", "q3",
        "What are the failure modes of token blocking and document-frequency "
        "filtering for common business names? Explain meta-blocking, "
        "conjunctive blocking keys, and multi-pass blocking, and identify "
        "practical strategies for maximizing recall at a fixed candidate "
        "budget.",
        tool="RESEARCH", research_effort="standard",
        search_queries=["meta-blocking supervised entity resolution"],
    ),
    Question(
        "blocking", "Blocking / Candidate Generation", "q4",
        "Compare DeepBlocker, UniBlocker, Sparkly, and other modern entity "
        "blocking approaches. Extract the most useful design patterns for a "
        "2M vs 10M scale system.",
        tool="RESEARCH", research_effort="standard",
        search_queries=[
            "DeepBlocker github",
            "UniBlocker code",
            "Sparkly entity resolution",
        ],
    ),
    # ------------------------------------------------------------------
    # TOPIC 2: BLOCKING RECALL AT FIXED CANDIDATE BUDGET
    # ------------------------------------------------------------------
    Question(
        "budget", "Blocking Recall at Fixed Candidate Budget", "q5",
        "How should blocking recall be evaluated when each reference entity "
        "can have zero, one, or multiple correct matches? Explain how to "
        "construct recall-versus-candidate-budget curves at k=10, k=25, "
        "k=50, k=100, k=200. Explain recall, reduction ratio, total "
        "candidate pairs, average candidates per entity, median candidates, "
        "95th percentile candidates, and candidate recall ceiling. Explain "
        "how candidate budget should be selected when final evaluation is "
        "macro F0.5.",
        tool="RESEARCH", research_effort="standard",
    ),
    Question(
        "budget", "Blocking Recall at Fixed Candidate Budget", "q6",
        "What blocking strategies are best for maximizing recall under a "
        "strict candidate budget when records contain noisy short business "
        "names, addresses, missing fields, abbreviations, and cross-script "
        "names?",
        tool="ANSWER",
    ),
    # ------------------------------------------------------------------
    # TOPIC 3: BUSINESS NAME NORMALIZATION
    # ------------------------------------------------------------------
    Question(
        "normalization", "Business Name Normalization", "q7",
        "For noisy business-name entity resolution across the US, India, and "
        "France, what normalization operations improve matching without "
        "increasing false positives? Analyze Unicode normalization, "
        "lowercasing, punctuation normalization, whitespace normalization, "
        "token normalization, legal suffix removal, abbreviations, token "
        "sorting, stopwords, repeated characters, numeric normalization, "
        "franchise indicators, and DBA names.",
        tool="RESEARCH", research_effort="standard",
    ),
    Question(
        "normalization", "Business Name Normalization", "q8",
        "What legal entity suffixes and abbreviations exist in the US, "
        "India, and France, including LLC, Inc, Ltd, Corp, Pvt Ltd, Private "
        "Limited, LLP, GmbH, SARL, SAS, SASU, EURL, SA, and SCI? Which are "
        "safe to remove during normalization and which should be retained "
        "as matching features?",
        tool="ANSWER",
    ),
    Question(
        "normalization", "Business Name Normalization", "q9",
        "What open-source company-name matching libraries exist, including "
        "cleanco and other company-name standardization or matching "
        "libraries? For each one report its GitHub repository, license, "
        "functionality, limitations, and whether it is appropriate for a "
        "hackathon competition.",
        tool="SEARCH",
        search_queries=[
            "cleanco github company name cleaning python",
            "open source company name standardization library",
            "company name matching library github license",
        ],
    ),
    Question(
        "normalization", "Business Name Normalization", "q10",
        "When does legal suffix removal cause false matches between "
        "distinct companies?",
        tool="ANSWER",
    ),
    # ------------------------------------------------------------------
    # TOPIC 4: MULTILINGUAL / CROSS-SCRIPT MATCHING
    # ------------------------------------------------------------------
    Question(
        "multilingual", "Multilingual / Cross-Script Matching", "q11",
        "For business names containing English, French, Hindi, and other "
        "Indian scripts, compare character n-gram similarity, "
        "transliteration, multilingual embeddings, phonetic "
        "representations, and hybrid matching. Focus specifically on entity "
        "resolution rather than generic semantic similarity.",
        tool="RESEARCH", research_effort="standard",
    ),
    Question(
        "multilingual", "Multilingual / Cross-Script Matching", "q12",
        "Compare open-source transliteration systems including IndicXlit, "
        "Aksharamukha, ICU, and other strong permissively licensed systems. "
        "Analyze accuracy, speed, license, typical errors, and suitability "
        "for business names.",
        tool="SEARCH",
        search_queries=[
            "IndicXlit github license",
            "Aksharamukha transliteration accuracy",
            "ICU transliteration library license",
        ],
    ),
    Question(
        "multilingual", "Multilingual / Cross-Script Matching", "q13",
        "What are typical Romanization errors including schwa deletion, "
        "vowel substitutions, consonant substitutions, v/w confusion, sh/s "
        "confusion, and long/short vowel confusion? Explain how these can "
        "become matching features for entity resolution.",
        tool="ANSWER",
    ),
    Question(
        "multilingual", "Multilingual / Cross-Script Matching", "q14",
        "Compare Double Metaphone, Soundex variants, Indic phonetic "
        "methods, and character n-grams for noisy multilingual business "
        "names.",
        tool="ANSWER",
    ),
    # ------------------------------------------------------------------
    # TOPIC 5: ADDRESS MATCHING
    # ------------------------------------------------------------------
    Question(
        "address", "Address Matching", "q15",
        "For large-scale business entity resolution, compare exact "
        "normalized address matching, token Jaccard, TF-IDF cosine, BM25, "
        "character n-grams, edit similarity, numeric-token overlap, "
        "house-number matching, postal-code matching, street-token "
        "matching, city matching, state/region matching, and unit/suite "
        "matching. Determine which features provide the strongest "
        "discriminatory power.",
        tool="RESEARCH", research_effort="standard",
    ),
    Question(
        "address", "Address Matching", "q16",
        "Compare generic address normalization across the US, India, and "
        "France. Investigate ZIP/ZIP+4, Indian PIN codes, French postal "
        "codes, CEDEX, bis/ter, rue, avenue, boulevard, suite, apartment, "
        "and Indian landmark patterns. Identify transformations that are "
        "safe across countries.",
        tool="RESEARCH", research_effort="standard",
    ),
    Question(
        "address", "Address Matching", "q17",
        "Investigate libpostal: what it does, its accuracy, license, "
        "training data, dependencies, and whether using its pretrained "
        "model could violate a competition rule prohibiting external "
        "databases or external data augmentation.",
        tool="SEARCH",
        search_queries=[
            "libpostal github license training data",
            "libpostal accuracy address parsing benchmark",
        ],
    ),
    # ------------------------------------------------------------------
    # TOPIC 6: PAIRWISE MATCHER
    # ------------------------------------------------------------------
    Question(
        "matcher", "Pairwise Matcher", "q18",
        "Compare logistic regression, LightGBM, XGBoost, CatBoost, neural "
        "pairwise models, Ditto, and cross-encoders for large-scale entity "
        "matching after candidate generation. Compare precision, recall, "
        "F0.5/F1 where available, throughput, memory, training complexity, "
        "inference complexity, and implementation complexity. Recommend a "
        "practical baseline and an advanced option.",
        tool="RESEARCH", research_effort="deep",
        search_queries=["Ditto entity matching github paper"],
    ),
    Question(
        "matcher", "Pairwise Matcher", "q19",
        "Design a feature set for LightGBM-style pairwise entity matching "
        "covering name features (exact equality, normalized equality, "
        "token overlap, token Jaccard, char 3-gram similarity, char 4-gram "
        "similarity, TF-IDF similarity, edit similarity, Jaro-Winkler, "
        "length ratio, token count difference, transliteration similarity, "
        "phonetic similarity), address features (exact equality, "
        "normalized equality, token similarity, char n-gram similarity, "
        "edit similarity, numeric overlap, postal-code overlap, "
        "house-number agreement, city similarity, state/region "
        "similarity), and other features (country equality, "
        "address-missing indicators, source pair, candidate retrieval "
        "score, retrieval rank, number of blocking passes that retrieved "
        "the pair).",
        tool="ANSWER",
    ),
    Question(
        "matcher", "Pairwise Matcher", "q20",
        "What hard-negative mining strategies work best for entity "
        "matching? Compare random negatives, blocker-mined negatives, "
        "model-mined negatives, in-batch negatives, hard-negative refresh, "
        "and false-negative handling.",
        tool="RESEARCH", research_effort="standard",
    ),
    # ------------------------------------------------------------------
    # TOPIC 7: LLM / SMALL MODEL MATCHING
    # ------------------------------------------------------------------
    Question(
        "llm", "LLM / Small Model Matching", "q21",
        "Which open models under 8B parameters with MIT or Apache-2.0 "
        "licenses could realistically be used for entity matching? "
        "Investigate model size, license, architecture, inference cost, "
        "fine-tuning feasibility, and classification/matching ability.",
        tool="RESEARCH", research_effort="standard",
    ),
    Question(
        "llm", "LLM / Small Model Matching", "q22",
        "Compare pairwise yes/no prompting, select-the-best-candidate "
        "prompting, cross-encoder scoring, using an LLM as an additional "
        "feature, and using an LLM as a final adjudicator. Determine "
        "whether an LLM is actually worth using after classical retrieval "
        "plus LightGBM, without recommending an LLM merely because it is "
        "fashionable.",
        tool="RESEARCH", research_effort="standard",
    ),
    # ------------------------------------------------------------------
    # TOPIC 8: MACRO F0.5 OPTIMIZATION
    # ------------------------------------------------------------------
    Question(
        "f05", "Macro F0.5 Optimization", "q23",
        "How should a prediction set be selected when each S1 entity can "
        "have zero, one, or multiple correct matches and the objective is "
        "per-entity macro F0.5? Compare global probability threshold, "
        "source-specific threshold, country-independent threshold, "
        "per-entity adaptive threshold, top-k selection, top-k plus "
        "threshold, expected F-beta optimization, and set-selection "
        "algorithms.",
        tool="RESEARCH", research_effort="deep",
    ),
    Question(
        "f05", "Macro F0.5 Optimization", "q24",
        "How should empty prediction sets be handled when an entity "
        "genuinely has no matches? Explain how to avoid false positives "
        "for singleton/no-match entities while maintaining high recall for "
        "entities with many matches.",
        tool="ANSWER",
    ),
    Question(
        "f05", "Macro F0.5 Optimization", "q25",
        "How should validation be designed so threshold tuning directly "
        "optimizes competition-level macro F0.5 instead of pairwise "
        "accuracy or F1?",
        tool="ANSWER",
    ),
    # ------------------------------------------------------------------
    # TOPIC 9: SCALE ENGINEERING
    # ------------------------------------------------------------------
    Question(
        "scale", "Scale Engineering", "q26",
        "What are the fastest CPU approaches for sparse top-k cosine "
        "similarity on millions of TF-IDF vectors? Compare scipy sparse, "
        "sparse_dot_topn, blockwise sparse matrix multiplication, FAISS "
        "alternatives, and other open-source approaches. Report memory, "
        "throughput, scalability, and implementation complexity.",
        tool="RESEARCH", research_effort="standard",
        search_queries=["sparse_dot_topn github benchmark"],
    ),
    Question(
        "scale", "Scale Engineering", "q27",
        "For 10 million 384-dimensional vectors, compare FAISS Flat, HNSW, "
        "IVF, and IVF-PQ for recall, memory, indexing time, query latency, "
        "and CPU/GPU suitability.",
        tool="RESEARCH", research_effort="standard",
    ),
    Question(
        "scale", "Scale Engineering", "q28",
        "How should a Python/Polars/PyArrow/DuckDB pipeline process tens or "
        "hundreds of millions of candidate pairs without materializing "
        "everything in RAM? Recommend data types, batching, partitioning, "
        "Parquet, memory mapping, sparse matrices, disk-backed processing, "
        "and multiprocessing.",
        tool="ANSWER",
    ),
    # ------------------------------------------------------------------
    # TOPIC 10: PRACTICAL COMPETITION SYSTEMS
    # ------------------------------------------------------------------
    Question(
        "competition", "Practical Competition Systems", "q29",
        "Find strong public entity-matching, record-linkage, "
        "location-matching, or business-matching competition solutions, "
        "prioritizing Foursquare location matching, Kaggle entity matching "
        "competitions, SIGMOD entity resolution contests, and large-scale "
        "record linkage competitions. Extract their candidate generation, "
        "features, model, negative sampling, post-processing, "
        "thresholding, graph techniques, and transitivity handling.",
        tool="RESEARCH", research_effort="deep",
        search_queries=[
            "Foursquare location matching kaggle winning solution",
            "SIGMOD entity resolution contest winning solution",
        ],
    ),
    Question(
        "competition", "Practical Competition Systems", "q30",
        "What post-processing techniques improve multi-match entity "
        "resolution, including one-to-one constraints, many-to-one "
        "constraints, graph clustering, connected components, "
        "transitivity, duplicate suppression, mutual nearest neighbors, "
        "and score calibration? Do not assume one-to-one matching, since "
        "many real competitions explicitly allow multiple matches per "
        "source entity.",
        tool="RESEARCH", research_effort="standard",
    ),
]

TOPIC_ORDER: List[str] = []
for _q in QUESTIONS:
    if _q.topic_slug not in TOPIC_ORDER:
        TOPIC_ORDER.append(_q.topic_slug)

TOPIC_TITLES = {q.topic_slug: q.topic_title for q in QUESTIONS}


def questions_for_topic(topic_slug: Optional[str]) -> List[Question]:
    if not topic_slug:
        return list(QUESTIONS)
    return [q for q in QUESTIONS if q.topic_slug == topic_slug]


def list_topics() -> List[str]:
    lines = []
    for slug in TOPIC_ORDER:
        count = len(questions_for_topic(slug))
        lines.append(f"{slug:14s} {TOPIC_TITLES[slug]}  ({count} questions)")
    return lines
