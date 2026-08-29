# Recall — Persistent, Benchmarked Agent Memory Layer
### Build Spec (feed this directly to Claude Code)

> **Instructions for Claude Code, if this is pasted as a prompt:** Build this in the phases listed under "Build Phases," in order, confirming with the user before starting each new phase. The benchmark harness (Phase 5) is not optional polish — it is the primary deliverable of this project. Do not build a general-purpose "memory OS," multi-tenant auth, or production-scale infra — see "Non-Goals."

---

## 1. What this project is

A pluggable memory layer that gives any AI agent persistent, evolving memory across sessions — remembering facts, correcting itself when new information contradicts old, and retrieving relevant memories using BOTH vector similarity search AND graph relationship traversal (not vector search alone, which is where most simple memory implementations stop).

**The core deliverable is not the memory layer itself — it's the benchmark report proving it works.** Build a small labeled test set of multi-session conversations with embedded facts (some of which get corrected/contradicted later), then measure recall accuracy, contradiction-resolution accuracy, and retrieval precision. A working memory demo with no benchmark numbers is a much weaker artifact than a smaller demo with a real, honest benchmark report.

## 2. Non-Goals (explicitly out of scope)

- A general-purpose "agent memory operating system" — build one focused, well-tested memory layer, not a platform
- Multi-tenant auth, billing, or multi-user isolation
- Production-scale vector/graph DB deployment — local Docker Compose is the target
- Supporting arbitrary agent frameworks — build it for ONE demo agent (a simple LangGraph conversational agent), and design the memory API cleanly enough that it's obviously reusable, without actually integrating five different frameworks
- Real-time memory updates during a live conversation turn — memory is written at the end of a session/turn and read at the start of the next; don't over-engineer live mid-conversation memory writes for v1

---

## 3. Architecture Overview

```
                         ┌─────────────────────────────┐
                         │       Demo Agent             │
                         │  (LangGraph conversational   │
                         │   agent — e.g. a support bot)│
                         └───────────┬──────────┬───────┘
                    at session start │          │ at session end
                     "retrieve"      │          │  "add memory"
                                     ▼          ▼
                         ┌──────────────────────────────┐
                         │      Memory Manager API        │
                         │        (FastAPI service)       │
                         │  - add_memory()                │
                         │  - retrieve_memory(query)      │
                         │  - resolve_contradiction()     │
                         └──────┬──────────────┬──────────┘
                                │              │
                 ┌──────────────┘              └───────────────┐
                 ▼                                              ▼
      ┌─────────────────────┐                       ┌─────────────────────────┐
      │   Vector Store        │                       │   Graph Store              │
      │  (Qdrant/ChromaDB)    │                       │   (Neo4j)                  │
      │  - semantic similarity│                       │  - entities                │
      │    search over        │                       │  - relationships           │
      │    memory chunks      │                       │  - "who/what is linked     │
      │                       │                       │     to what"               │
      └─────────────────────┘                       └─────────────────────────┘
                 ▲                                              ▲
                 └──────────────────┬───────────────────────────┘
                                     │
                       ┌─────────────────────────────┐
                       │  Entity Extraction & Linking  │
                       │  (runs during add_memory())   │
                       │  - pulls entities out of new  │
                       │    memory, links to graph      │
                       │  - checks for contradiction    │
                       │    against existing facts       │
                       └─────────────────────────────┘

                       ┌─────────────────────────────┐
                       │   PostgreSQL                  │
                       │  - raw conversation logs       │
                       │  - memory audit trail           │
                       │    (what was added/superseded)  │
                       │  - benchmark run history         │
                       └─────────────────────────────┘

Separate, standalone module (the KEY deliverable):
┌───────────────────────────────────────────────────────────────────────┐
│  Benchmark Harness (CLI, run via `make benchmark`)                     │
│  - test dataset: multi-session synthetic conversations, each with       │
│    embedded facts, some of which are later corrected/contradicted       │
│  - probe questions: asked in a LATER session, testing whether the       │
│    memory layer recalls the CURRENT correct fact (not a stale one)      │
│  - run_benchmark.py — feeds sessions in order, then asks probe          │
│    questions, scores against ground truth                              │
│  - generates report.md: recall accuracy, contradiction-resolution       │
│    accuracy, retrieval precision, false-memory rate                    │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 4. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Memory API service | FastAPI (Python) | Simple, well-suited to wrapping vector/graph clients |
| Vector store | Qdrant or ChromaDB | Already in your skillset; semantic similarity retrieval layer |
| Graph store | Neo4j | Already in your skillset; entity/relationship retrieval layer |
| Entity extraction | LLM-based structured extraction (Claude API) during `add_memory()` | Extract entities + relationships from each new memory, similar to how modern memory frameworks (e.g., Mem0-style entity linking) work — this is the piece that makes retrieval relationship-aware, not just similarity-based |
| Agent orchestration | LangGraph | Already your primary agent framework (reused from Praxis) |
| Demo agent LLM | Anthropic Claude API | Consistent with the rest of your stack |
| Relational storage | PostgreSQL | Conversation logs, memory audit trail, benchmark history |
| Benchmark scoring | Custom Python scoring script (exact-match / LLM-graded correctness against ground truth) | No single standard library covers this — write your own scorer, but structure it like the field's emerging benchmarks (multi-session recall tests) |
| Containerization | Docker Compose (API, Qdrant/Chroma, Neo4j, Postgres) | Reproducible one-command local run |

**Note:** verify current library versions/APIs (Qdrant client, Neo4j driver, LangGraph memory-related APIs) when starting — this space is moving fast and package interfaces change often; don't assume training-data-era API signatures are current.

---

## 5. Repository Structure

```
recall/
├── memory_service/
│   ├── main.py                # FastAPI app: add_memory, retrieve_memory endpoints
│   ├── vector_store.py         # Qdrant/ChromaDB wrapper
│   ├── graph_store.py          # Neo4j wrapper — entity/relationship CRUD
│   ├── entity_extraction.py    # LLM-based entity/relationship extraction from new memories
│   ├── contradiction.py        # detects conflicting facts, decides supersede vs. coexist
│   ├── retrieval_router.py     # decides vector-only vs. graph-only vs. hybrid retrieval per query
│   └── models.py               # Pydantic schemas for memory records
├── demo_agent/
│   ├── graph.py                # LangGraph conversational agent using Recall as a tool
│   └── run_session.py          # CLI to simulate a conversation session (for manual testing)
├── benchmark/
│   ├── dataset/
│   │   ├── sessions/            # synthetic multi-session conversations (JSON), each session
│   │   │                        # tagged with session number, facts introduced, and any
│   │   │                        # facts that CONTRADICT an earlier session
│   │   └── probes.csv           # probe question, expected current-correct answer, which
│   │                            # session(s) it depends on
│   ├── run_benchmark.py         # feeds sessions in order into Recall, then asks probes
│   ├── score.py                 # scoring logic (recall accuracy, contradiction handling, etc.)
│   └── report/
│       ├── report.md            # THE key deliverable — human-readable results
│       └── report.json
├── docker-compose.yml
├── requirements.txt
├── Makefile                     # `make dev`, `make benchmark`, `make report`
└── README.md                    # architecture diagram, benchmark numbers, trade-offs, what you'd
                                  # add for production (multi-tenant, real-time memory writes, etc.)
```

---

## 6. Component Specs

### 6.1 Memory Manager API (`memory_service/main.py`)
- `POST /memory/add` — takes a raw memory (text, e.g. a conversation summary or extracted fact) plus metadata (session id, timestamp, user id). Triggers entity extraction, contradiction check, then writes to both vector store and graph store.
- `GET /memory/retrieve?query=...` — takes a natural-language query, routes it through the retrieval router (vector, graph, or hybrid), returns ranked, merged memory results.
- `GET /memory/audit/{entity}` — returns the full history of what's been stored/superseded about a given entity — useful for debugging and for the benchmark harness to verify contradiction handling worked correctly.

### 6.2 Entity Extraction & Linking (`entity_extraction.py`)
- On `add_memory()`, use the LLM with structured output to extract: entities mentioned (people, projects, preferences, facts), and their relationships to each other
- Link extracted entities to existing graph nodes where they match (e.g., "the user's project" should link to the SAME graph node across sessions, not create duplicates) — this de-duplication step is one of the harder, more important pieces; don't skip it

### 6.3 Contradiction Handling (`contradiction.py`)
- When a new memory is added, check whether it conflicts with an existing stored fact about the same entity (e.g., "user prefers email notifications" stored earlier, new memory says "user prefers SMS notifications")
- Resolution policy for v1 (keep it simple and explicit, not magic): the newer memory supersedes the older one for that specific fact, but the old fact is NOT deleted — it's marked `superseded_at` in the audit trail, preserving history
- This is exactly the "curation" problem the field is actively researching — you don't need a novel algorithm, a clear, explicit, well-tested policy is a completely legitimate and honest project scope

### 6.4 Retrieval Router (`retrieval_router.py`)
- Simple, explicit routing logic (not an ML classifier for v1): if the query is asking about a specific named entity/relationship ("what project is X working on"), prefer graph traversal; if it's a general semantic query ("what does the user care about"), use vector search; for ambiguous queries, run both and merge/rank results
- Be ready to explain in an interview exactly why you chose rule-based routing over an LLM-based router for this — latency and predictability, consistent with your "rules decide" philosophy from Praxis

### 6.5 Demo Agent (`demo_agent/`)
- A simple LangGraph conversational agent (pick one scenario — e.g., a personal assistant that helps schedule tasks and remembers user preferences) that calls `retrieve_memory` at the start of a session and `add_memory` at the end
- Keep the agent itself simple — it exists to prove the memory layer works end-to-end, not to be sophisticated on its own

### 6.6 Benchmark Harness (`benchmark/`) — the most important part
- Build ~15-20 synthetic multi-session conversation sequences yourself. Each sequence: 3-5 short sessions, each introducing or updating a fact about a consistent set of entities (a user, their projects, their preferences). At least a third of sequences should include a deliberate contradiction (a fact stated in session 1, corrected in session 3).
- `probes.csv`: for each sequence, write probe questions to ask AFTER all sessions have been fed in, testing whether the memory layer returns the CURRENT correct answer (not the outdated one)
- `run_benchmark.py`: feeds each sequence's sessions into Recall via the real API (not mocked), then asks the probes, records what was retrieved
- `score.py`: compute — **recall accuracy** (did retrieval surface the relevant memory at all), **correctness accuracy** (was the CURRENT fact returned, not a stale contradicted one), **false-memory rate** (did retrieval ever surface an irrelevant or hallucinated-sounding memory)
- `report.md`: a results table by category (simple recall vs. contradiction-resolution vs. multi-hop entity queries), with 2-3 sentences interpreting where the system is weakest — **an honest report showing where it fails is more credible and more interesting to an interviewer than a report claiming near-perfect scores**

---

## 7. Build Phases (demo-check after each phase before continuing)

**Phase 1 — Vector-only memory, sanity check**
Build `add_memory`/`retrieve_memory` using ONLY the vector store (no graph yet). Confirm basic storage and semantic retrieval work via a simple script before adding complexity.

**Phase 2 — Add the graph layer + entity linking**
Wire up Neo4j, build entity extraction and linking, implement the hybrid retrieval router. Confirm a query that needs relationship traversal (not just similarity) actually returns better results with graph included vs. vector-only.

**Phase 3 — Contradiction handling**
Implement the contradiction detection and supersede policy, with the audit trail. Manually test: add a fact, add a contradicting fact, confirm retrieval returns the new one and the audit endpoint shows the history correctly.

**Phase 4 — Demo agent integration**
Wire the LangGraph demo agent to call Recall at session start/end. Run a few real multi-session conversations manually and sanity-check behavior.

**Phase 5 — Benchmark harness (the key deliverable)**
Build the synthetic dataset, the runner, and the scorer. Generate your first real `report.md`. Iterate on the memory layer based on where the benchmark shows weaknesses — this iteration loop, and being able to talk about what you found and fixed, is itself a strong interview story.

**Phase 6 — Polish**
Docker Compose for one-command local run. README with the architecture diagram, your actual benchmark numbers, and a "Production Considerations" section (real-time memory writes, multi-tenant isolation, a learned/ML-based retrieval router instead of rule-based, larger-scale benchmark).

---

## 8. Acceptance Criteria

- Working memory API: can add memories across multiple simulated sessions and retrieve them correctly, using both vector and graph paths
- Demonstrated contradiction handling: a concrete before/after example showing an outdated fact being correctly superseded, with the audit trail intact
- `report.md` with REAL numbers (not placeholders) from your own benchmark dataset, broken down by category, with honest interpretation of where the system underperforms
- Entire thing runs via `docker-compose up` + a single benchmark command — reproducible for someone else to verify

## 9. What to tell Claude Code first

Paste this whole document, then add:
> "Start with Phase 1 only — vector-only memory add/retrieve, tested with a simple script. Confirm it works before we add the graph layer."
