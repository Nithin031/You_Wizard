# You.com Entity Resolution Research Assistant

A local research assistant, built on the official `youdotcom` Python SDK, that
automatically runs the 30-question research program for a Business Entity
Resolution hackathon (blocking, normalization, multilingual/address matching,
pairwise matching, macro F0.5 optimization, scale engineering, and competition
systems) and produces one consolidated Markdown report with citations.

It only researches public algorithms, papers, libraries, and competition
write-ups. It never sends your actual dataset (business names, addresses,
entity IDs, or records) to You.com.

## 1. Installation

```bash
cd you_entity_research
python -m venv .venv

# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Requires Python 3.10+.

## 2. API-key setup

Set the `YDC_API_KEY` environment variable, or copy `.env.example` to `.env`
and fill it in -- either works.

**Linux/macOS:**
```bash
export YDC_API_KEY="YOUR_API_KEY"
```

**Windows PowerShell:**
```powershell
$env:YDC_API_KEY="YOUR_API_KEY"
```

**Or, via .env file:**
```bash
cp .env.example .env   # Windows: copy .env.example .env
# then edit .env and paste your key
```

## 3. Running the tool

```bash
python run_research.py
```

This validates the SDK and API key, runs all 30 questions across all 10
topics with the appropriate You.com tool auto-selected per question, and
writes:

- `output/answers/<topic>_<qid>.json` -- one structured result per question
- `output/raw/<topic>_<qid>.json` -- the raw API response(s) behind it
- `output/sources/<topic>.json` -- full-page content fetched via Contents
- `output/final/entity_resolution_research_report.md` -- the final report

Useful flags:

```bash
python run_research.py --concurrency 5      # more parallel API calls
python run_research.py --no-contents        # skip the Contents fetch stage
python run_research.py --no-synthesis       # skip building the final report
python run_research.py --no-cache           # bypass the response cache
```

## 4. Running individual topics

```bash
python run_research.py --list-topics
python run_research.py --topic blocking
python run_research.py --topic f05
```

`--list-topics` works without an API key set.

## 5. Resume

If a run stops halfway (network issue, Ctrl-C, rate limit), continue from
the last successful question:

```bash
python run_research.py --resume
```

Progress is tracked in `output/progress.json` (`pending` / `running` /
`completed` / `failed` per question). Failed questions are retried
automatically on the next `--resume` run.

## 6. Refresh cache

Every API call is cached by a hash of its parameters under
`output/raw/cache/`. Re-running the same question costs nothing. To force
fresh calls (e.g. you expect updated web results):

```bash
python run_research.py --refresh
```

## 7. Budget control

Cap the estimated relative API cost for a run:

```bash
python run_research.py --budget 25
```

Before running, the tool prints the estimated number of Research/Search/
Answer/Contents calls and their relative cost. If the estimate exceeds
`--budget`, it reduces optional work in this order and prints what it cut:

1. Disable the Contents follow-up fetch stage.
2. Drop follow-up Search queries on non-core topics.
3. Skip entire non-core topics (multilingual, LLM, scale, competition),
   least-important first, while keeping all core topics
   (blocking, budget, normalization, address, matcher, f05) intact.

It never silently exceeds the configured budget -- if even the core topics
alone exceed it, it says so and proceeds with that minimum rather than
guessing further cuts to required questions.

## 8. Output structure

```
output/
├── raw/                 # raw API responses per question, plus the cache/
│   └── cache/<hash>.json
├── sources/<topic>.json # full-page content fetched via Contents per topic
├── answers/<topic>_<qid>.json  # structured per-question results
├── progress.json        # resume state
└── final/
    └── entity_resolution_research_report.md
```

Each structured result in `output/answers/` looks like:

```json
{
  "topic": "blocking",
  "question_id": "q1",
  "question": "...",
  "tool_used": "RESEARCH",
  "answer": "...",
  "sources": [{"title": "...", "url": "...", "source_type": "...", "relevance": "...", "quality": "A"}],
  "key_findings": [],
  "recommendations": [],
  "implementation_implications": [],
  "confidence": "high",
  "raw_response_file": "output/raw/blocking_q1.json"
}
```

## 9. Troubleshooting

- **"the official You.com SDK is not installed"** -- run
  `pip install -r requirements.txt`.
- **"YDC_API_KEY is not set"** -- see section 2 above; the tool refuses to
  guess or run with an empty key.
- **401/403 errors** -- your API key is invalid or lacks access to one of
  the four APIs (Search, Contents, Answer, Research); verify it in your
  You.com dashboard.
- **429 / rate limited** -- the SDK automatically retries with exponential
  backoff and honors `Retry-After`. Lower `--concurrency` if you hit this
  often.
- **A question keeps failing** -- check `output/progress.json` for its
  status/error, then re-run with `--resume`; only failed/pending questions
  are retried, completed ones are reused from `output/answers/`.
- **Report looks thin / says "No research data collected"** -- that topic's
  questions either failed, were cut by `--budget`, or the run hasn't
  finished yet; the synthesizer never invents content for missing data.
- **Disk full / stale cache** -- delete `output/raw/cache/` to reclaim
  space; the next run will simply re-fetch.
