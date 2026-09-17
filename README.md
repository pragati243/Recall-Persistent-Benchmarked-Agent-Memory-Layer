# Recall — Persistent, Benchmarked Agent Memory Layer

A pluggable memory layer for AI agents: persistent facts across sessions, contradiction-aware
updates, and hybrid vector + graph retrieval — proven with a benchmark harness, not just a demo.

Full design doc: [recall_architecture_spec.md](recall_architecture_spec.md)

## Status

- [x] Phase 1 — vector-only memory add/retrieve
- [x] Phase 2 — graph layer + entity linking
- [x] Phase 3 — contradiction handling + audit trail
- [x] Phase 4 — LangGraph demo agent
- [x] Phase 5 — benchmark harness run against real Qdrant/Neo4j/Postgres/Groq; generated
      `benchmark/report/report.md` and `report.json` (see [Benchmark](#benchmark) below)
- [x] Phase 6 — Docker Compose + this README

## Architecture

```
demo_agent (LangGraph)                  benchmark (standalone CLI)
  retrieve @ session start                18 sequences → run_benchmark.py
  add_memory @ session end                            → score.py → report.md
         │      ▲
         ▼      │
  ┌───────────────────────────┐
  │   memory_manager           │
  │  (memory_service/main.py — │
  │   FastAPI: /memory/*)      │
  └──┬───────────┬─────────┬───┘
     ▼           ▼         ▼
  Vector Store  Entity     Contradiction
  (Qdrant)      Extraction  Policy
                (Groq,          │
                 structured) ───┴──▶ Graph Store (Neo4j)
                                       │
                                       ▼
                                 Audit Trail (Postgres)
```

`retrieval_router` picks vector, graph, or both per query using explicit rules (not a
learned classifier) — see [Design decisions](#design-decisions-and-known-limitations).

## Quickstart

```bash
git clone <this repo> && cd recall
cp .env.example .env        # then set GROQ_API_KEY
docker compose up -d --wait qdrant neo4j postgres api
uv run python benchmark/run_benchmark.py && uv run python benchmark/score.py
```

Or with `make` (optional convenience layer — same commands underneath):
`make dev`, `make benchmark`, `make report`, `make test`, `make down`.

The API itself runs at `http://localhost:8000/docs` once `api` is up. The benchmark and
demo agent call `memory_service` as a Python library directly (not over HTTP) — see
[Design decisions](#design-decisions-and-known-limitations) for why.

## Repository structure

```
memory_service/     FastAPI service: add_memory, retrieve_memory, audit
  vector_store.py      Qdrant wrapper (local-file or server mode)
  graph_store.py       Neo4j wrapper — entities/relationships, MERGE-based dedup
  entity_extraction.py Groq structured extraction (tool use)
  contradiction.py     supersede policy
  audit_store.py       Postgres append-only audit trail
  retrieval_router.py  rule-based vector/graph/hybrid routing
demo_agent/          LangGraph personal-assistant scenario + CLI runner
benchmark/           dataset (18 sequences), runner, scorer — the key deliverable
scripts/             one-off manual sanity checks, one per phase
docker-compose.yml   qdrant, neo4j, postgres, api
```

## Design decisions and known limitations

Documented here rather than scattered across commits, since these are the things worth
being able to explain, not accidents:

- **Entity linking is exact-match, not semantic.** Entities dedup via a Neo4j `MERGE` on
  `(user_id, normalized name)`. "The user's project" and "Atlas" won't link to the same
  node unless the LLM happens to name them identically. Real semantic resolution
  (synonyms, pronouns) is exactly the "curation problem" the field is still researching —
  see [Production Considerations](#production-considerations).
- **Contradiction matching is exact-match on relation string.** The policy (spec §6.3) is
  intentionally simple: a new fact supersedes an old one about the same `(entity,
  relation)` if it points at a different target, and nothing is deleted —
  `superseded_at` is set in both Postgres and the Neo4j edge. This only works if the LLM
  extracts a *consistent* relation label for the same kind of fact across sessions.
- **Retrieval routing is rule-based, not learned.** `retrieval_router` checks for
  relationship keywords ("who", "manages", "reports to", ...) plus a known-entity mention
  to decide graph vs. vector vs. both. Chosen over an LLM router for latency and
  predictability — you can read the three lines of logic and know exactly what it'll do.
  The real cost: plain-language queries about a fact that *has* a contradiction history
  stay vector-only, and Qdrant has no concept of supersession — see the benchmark
  prediction below.
- **Qdrant runs in two modes.** Docker-backed server mode is the documented default
  (`QDRANT_URL=http://localhost:6333`), so scripts and the API exercise the same store.
  Clearing `QDRANT_URL` opts into local-file mode (`QDRANT_PATH`), which locks storage to
  one process and is useful only for isolated experiments.
- **The benchmark and demo agent call `memory_manager`/`retrieval_router` directly as a
  Python library, not over HTTP against the `api` container.** "Via the real API, not
  mocked" (spec §6.6) is satisfied either way — real stores, real Groq calls, nothing
  stubbed — and skipping the HTTP hop keeps both simpler. The FastAPI layer exists for
  external callers (interview demos, a future non-Python client).
- **Scoring is exact substring match, not LLM-graded.** Cheap, deterministic, and
  consistent with routing on explicit rules elsewhere in this project. See
  `benchmark/score.py`'s docstring.

## Benchmark

**The primary deliverable of this project (spec §1) is this report, not the memory layer
itself.** 18 hand-written multi-session sequences, 6 each across three categories:

- **simple_recall** — one fact plus two distractor sessions, plain vector retrieval
- **contradiction** — a fact stated in session 1, corrected in session 3 (exactly a third
  of the dataset, per spec's minimum)
- **multi_hop** — the answer needs a 2-hop graph traversal; no single session mentions
  both the query subject and the answer

```bash
docker compose up -d --wait qdrant neo4j postgres
uv run python benchmark/run_benchmark.py   # feeds sequences, asks probes, writes raw_results.json
uv run python benchmark/score.py            # scores vs. ground truth, writes report.md + report.json
```

The real artifacts are checked in at [`benchmark/report/report.md`](benchmark/report/report.md)
and [`benchmark/report/report.json`](benchmark/report/report.json). They were generated against
live local Qdrant, Neo4j, PostgreSQL, and Groq; the figures below are measured results, not
placeholders.

**A falsifiable prediction, written before any real run:** the `contradiction` category
will underperform the other two. Plain-language probes ("how does the user want to be
notified?") don't hit `retrieval_router`'s relationship keywords, so they stay
vector-only — and Qdrant has no concept of supersession, so a stale fact can rank above
the current one. `multi_hop` and `simple_recall` shouldn't have this problem.

### Actual results — 2026-09-17

| Category | Probes | Recall Accuracy | Correctness Accuracy | False-Memory Rate |
|---|---:|---:|---:|---:|
| simple_recall | 6 | 100% | 83% | 0% |
| contradiction | 6 | 100% | 33% | 0% |
| multi_hop | 6 | 100% | 0% | 0% |
| overall | 18 | 100% | 39% | 0% |

The prediction partially held: contradiction retrieval underperformed simple recall
(33% versus 83%) because vector-only probes ranked stale facts first. It did not
outperform multi-hop as predicted; graph routing surfaced related nodes but did not
traverse and rank the expected answer, leaving multi-hop at 0% correctness.

## Production Considerations

Explicitly out of scope for this project (see spec §2 Non-Goals), but worth naming what
v1's simplifications would cost at real scale:

- **Real-time memory writes.** Memory is written at session end, not mid-conversation.
  A long-running session that changes a fact partway through won't reflect it until the
  next session starts.
- **Multi-tenant isolation.** `user_id` is an unenforced string field, not an auth
  boundary — fine for one demo user, not for a shared deployment.
- **A learned retrieval router.** The rule-based router is explainable and fast, but its
  keyword list is hand-maintained and will miss phrasings it wasn't written for. An
  ML-based router (or an LLM router, accepting the latency cost) would generalize better
  once there's enough labeled query traffic to train or prompt it well.
- **Semantic entity resolution.** Exact-match linking (see above) will fragment the graph
  under real usage — the same real-world entity referred to five different ways becomes
  five nodes. Needs embedding-based or LLM-assisted entity resolution with a real
  confidence threshold, not string equality.
- **A larger, adversarial benchmark.** 18 sequences is enough to get a first honest
  signal, not enough to be statistically confident about a specific number. Scaling this
  up, plus adding harder multi-hop chains (3+ hops) and paraphrased probes (not just
  literal keyword overlap with the stored text), would stress-test the exact-match scorer
  itself, which currently rewards verbatim phrasing.

## Tests

```bash
uv run pytest
```
