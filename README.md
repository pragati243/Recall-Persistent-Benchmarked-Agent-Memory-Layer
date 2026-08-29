# Recall — Persistent, Benchmarked Agent Memory Layer

A pluggable memory layer for AI agents: persistent facts across sessions, contradiction-aware
updates, and hybrid vector + graph retrieval — proven with a benchmark harness, not just a demo.

Full design doc: [recall_architecture_spec.md](recall_architecture_spec.md)

## Status

Building in phases (see spec, §7).

- [x] Phase 1 — vector-only memory add/retrieve (Qdrant + FastEmbed)
- [x] Phase 2 — graph layer + entity linking
- [x] Phase 3 — contradiction handling
- [ ] Phase 4 — demo agent integration
- [ ] Phase 5 — benchmark harness
- [ ] Phase 6 — Docker Compose + polish

## Phase 1 — Quickstart

```bash
uv sync
cp .env.example .env
uv run python scripts/sanity_check.py       # add + retrieve sanity check
uv run uvicorn memory_service.main:app --reload   # POST /memory/add, GET /memory/retrieve
```

## Phase 2 — Graph layer

Requires Neo4j (Docker) and an Anthropic API key for entity extraction.

```bash
docker compose up -d --wait neo4j
# set ANTHROPIC_API_KEY in .env
uv sync
uv run python scripts/sanity_check_graph.py   # graph vs. vector-only, side by side
```

Entity linking (dedup) is a deliberately simple v1 policy: exact match on normalized
name per user, enforced via a Neo4j `MERGE`. Synonym/pronoun resolution ("the user's
project" == "Atlas") is a known limitation — see Production Considerations (Phase 6).

## Phase 3 — Contradiction handling

Requires Postgres in addition to Neo4j + an Anthropic key.

```bash
docker compose up -d --wait neo4j postgres
uv sync
uv run python scripts/sanity_check_contradiction.py
uv run uvicorn memory_service.main:app --reload   # GET /memory/audit/{entity}
```

Policy (spec §6.3): a new fact supersedes an older one about the same (entity, relation)
if it points at a different target. The old fact is never deleted — `superseded_at` is
set in both the Postgres audit trail and the Neo4j edge, so retrieval only ever
traverses current facts but the full history stays queryable via `/memory/audit/{entity}`.
Matching is on the exact normalized relation string extracted by the LLM — a known
limitation if the same kind of fact gets extracted under inconsistent relation labels
across sessions.

## Tests

```bash
uv run pytest
```
