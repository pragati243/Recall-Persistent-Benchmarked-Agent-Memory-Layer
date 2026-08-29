# Recall — Persistent, Benchmarked Agent Memory Layer

A pluggable memory layer for AI agents: persistent facts across sessions, contradiction-aware
updates, and hybrid vector + graph retrieval — proven with a benchmark harness, not just a demo.

Full design doc: [recall_architecture_spec.md](recall_architecture_spec.md)

## Status

- [x] Phase 1 — vector-only memory add/retrieve
- [x] Phase 2 — graph layer + entity linking
- [x] Phase 3 — contradiction handling + audit trail
- [x] Phase 4 — LangGraph demo agent
- [ ] Phase 5 — benchmark harness built; **`report.md` not generated yet** — needs a live run
      against real Neo4j/Postgres/Anthropic (see [Benchmark](#benchmark) below)
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
                (Claude,        │
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
cp .env.example .env        # then set ANTHROPIC_API_KEY
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
  entity_extraction.py Claude structured extraction (tool use)
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
- **Qdrant runs in two modes.** Local-file mode (default, `QDRANT_PATH`) needs no server
  but locks its storage to one process — fine for scripts, wrong for a real service.
  Setting `QDRANT_URL` switches to server mode, which is what `docker-compose`'s `api`
  service uses.
- **The benchmark and demo agent call `memory_manager`/`retrieval_router` directly as a
  Python library, not over HTTP against the `api` container.** "Via the real API, not
  mocked" (spec §6.6) is satisfied either way — real stores, real Claude calls, nothing
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

**`report.md` is intentionally not committed.** It can only be generated by a real run
against live Neo4j/Postgres/Anthropic, none of which exist in the environment this was
built in. Fabricating numbers would contradict the entire point of this phase — the spec
is explicit that an honest report beats a good-looking fake one. `score.py`'s scoring
logic was verified against a synthetic fixture (not committed) covering all five cases it
needs to get right: a clean top-1 hit, a stale-fact-ranked-first miss, graph-hit
precedence over a vector hit, a total miss, and a planted cross-sequence contamination
case — all five scored correctly.

**A falsifiable prediction, written before any real run:** the `contradiction` category
will underperform the other two. Plain-language probes ("how does the user want to be
notified?") don't hit `retrieval_router`'s relationship keywords, so they stay
vector-only — and Qdrant has no concept of supersession, so a stale fact can rank above
the current one. `multi_hop` and `simple_recall` shouldn't have this problem. Once this
runs for real, this section gets replaced with the actual table and an interpretation of
whether that held.

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
