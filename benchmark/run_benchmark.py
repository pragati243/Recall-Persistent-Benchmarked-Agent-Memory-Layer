"""Feeds each sequence's sessions into Recall via the real API (no mocking),
then immediately asks that sequence's probe(s) and records what was
retrieved. Scoring against ground truth happens separately in score.py.

For a clean measurement, wipe local state first:
    rm -rf .data/qdrant && docker compose down -v && docker compose up -d --wait neo4j postgres
Re-running without wiping still works (stores are isolated per bench-<sequence_id>
user id) but accumulates duplicate/repeat facts within the same sequence.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

from memory_service.memory_manager import add_memory
from memory_service.models import MemoryCreate
from memory_service.retrieval_router import retrieval_router

BASE = Path(__file__).parent
SESSIONS_DIR = BASE / "dataset" / "sessions"
PROBES_PATH = BASE / "dataset" / "probes.csv"
REPORT_DIR = BASE / "report"


def load_sequences() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(SESSIONS_DIR.glob("*.json"))}


def load_probes_by_sequence() -> dict[str, list[dict]]:
    by_sequence: dict[str, list[dict]] = defaultdict(list)
    with PROBES_PATH.open(newline="", encoding="utf-8") as f:
        for probe in csv.DictReader(f):
            by_sequence[probe["sequence_id"]].append(probe)
    return by_sequence


def run() -> list[dict]:
    sequences = load_sequences()
    probes_by_sequence = load_probes_by_sequence()
    results = []

    for sequence_id, sequence in sequences.items():
        user_id = f"bench-{sequence_id}"
        session_texts = [s["text"] for s in sequence["sessions"]]

        for session in sequence["sessions"]:
            add_memory(MemoryCreate(text=session["text"], session_id=session["session_id"], user_id=user_id))

        probes = probes_by_sequence.get(sequence_id, [])
        for probe in probes:
            outcome = retrieval_router.retrieve(probe["question"], user_id=user_id)
            results.append({
                "sequence_id": sequence_id,
                "category": probe["category"],
                "question": probe["question"],
                "expected_answer": probe["expected_answer"],
                "stale_answer": probe["stale_answer"],
                "session_texts": session_texts,
                "mode": outcome["mode"],
                "graph_hits": outcome["graph_hits"],
                "vector_hits": [{"text": h.text, "score": h.score} for h in outcome["vector_hits"]],
            })

        print(f"[{sequence_id}] fed {len(session_texts)} sessions, asked {len(probes)} probe(s)")

    return results


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = run()
    out_path = REPORT_DIR / "raw_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {len(results)} probe results to {out_path}")
    print("Next: uv run python benchmark/score.py")


if __name__ == "__main__":
    main()
