# Recall — Persistent, Benchmarked Agent Memory Layer

A pluggable memory layer for AI agents: persistent facts across sessions, contradiction-aware
updates, and hybrid vector + graph retrieval — proven with a benchmark harness, not just a demo.

Full design doc: [recall_architecture_spec.md](recall_architecture_spec.md)

## Status

Building in phases (see spec, §7).

- [x] Phase 1 — vector-only memory add/retrieve (Qdrant + FastEmbed)
- [ ] Phase 2 — graph layer + entity linking
- [ ] Phase 3 — contradiction handling
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

## Tests

```bash
uv run pytest
```
