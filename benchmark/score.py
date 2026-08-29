"""Scores benchmark/report/raw_results.json against ground truth and writes
report.json + report.md. Exact-match scoring (not LLM-graded): cheap,
deterministic, and consistent with routing on explicit rules rather than a
model elsewhere in this project - see README for the LLM-graded alternative
noted as a Production Consideration.

Metrics per spec §6.6:
  recall accuracy       - did retrieval surface the expected answer at all
  correctness accuracy   - was the expected answer in the TOP-ranked hit
                            (graph hits rank first, matching the router's
                            own precedence when it picks graph mode)
  false-memory rate       - did a vector hit return text that isn't one of
                            this sequence's own memories (cross-contamination;
                            does not cover "on-topic but wrong" - that's
                            already captured by correctness accuracy)
"""

import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent
REPORT_DIR = BASE / "report"
RAW_RESULTS_PATH = REPORT_DIR / "raw_results.json"


def _combined_hits(row: dict) -> list[str]:
    graph_texts = [f"{h['name']} ({h['type']})" for h in row["graph_hits"]]
    vector_texts = [h["text"] for h in row["vector_hits"]]
    return graph_texts + vector_texts


def score_row(row: dict) -> dict:
    combined = _combined_hits(row)
    combined_blob = " ".join(combined).lower()
    expected = row["expected_answer"].lower()

    recall_hit = expected in combined_blob
    correctness_hit = bool(combined) and expected in combined[0].lower()

    own_texts = {t.lower() for t in row["session_texts"]}
    false_memory = any(h["text"].lower() not in own_texts for h in row["vector_hits"])

    return {**row, "recall_hit": recall_hit, "correctness_hit": correctness_hit, "false_memory": false_memory}


def summarize(scored: list[dict]) -> dict:
    by_category = defaultdict(list)
    for row in scored:
        by_category[row["category"]].append(row)

    def stats(rows: list[dict]) -> dict:
        n = len(rows)
        return {
            "n": n,
            "recall_accuracy": sum(r["recall_hit"] for r in rows) / n,
            "correctness_accuracy": sum(r["correctness_hit"] for r in rows) / n,
            "false_memory_rate": sum(r["false_memory"] for r in rows) / n,
        }

    summary = {category: stats(rows) for category, rows in sorted(by_category.items())}
    summary["overall"] = stats(scored)
    return summary


def render_report_md(summary: dict, scored: list[dict]) -> str:
    lines = [
        "# Recall Benchmark Report",
        "",
        f"{len(scored)} probes across {len(summary) - 1} categories. Exact-match scoring "
        "against hand-written ground truth (see benchmark/dataset/probes.csv).",
        "",
        "| Category | N | Recall Accuracy | Correctness Accuracy | False-Memory Rate |",
        "|---|---|---|---|---|",
    ]
    for category in [*(k for k in summary if k != "overall"), "overall"]:
        s = summary[category]
        lines.append(
            f"| {category} | {s['n']} | {s['recall_accuracy']:.0%} | "
            f"{s['correctness_accuracy']:.0%} | {s['false_memory_rate']:.0%} |"
        )

    lines += ["", "## Failures (correctness miss)", ""]
    failures = [r for r in scored if not r["correctness_hit"]]
    if not failures:
        lines.append("None.")
    else:
        for r in failures:
            top_hit = _combined_hits(r)[0] if _combined_hits(r) else "(no hits)"
            lines.append(
                f"- **{r['sequence_id']}** ({r['category']}): {r['question']!r} — "
                f"expected {r['expected_answer']!r}, mode={r['mode']}, top hit={top_hit!r}"
            )

    lines += ["", "## Interpretation", ""]
    categories = {k: v for k, v in summary.items() if k != "overall"}
    weakest_category, weakest = min(categories.items(), key=lambda kv: kv[1]["correctness_accuracy"])
    lines.append(
        f"Weakest category: **{weakest_category}** at {weakest['correctness_accuracy']:.0%} "
        f"correctness accuracy (n={weakest['n']}). See the failures above for exactly which "
        "probes missed and what ranked first instead - that's the starting point for "
        "deciding whether it's a routing issue, an extraction-consistency issue, or a real "
        "gap in the contradiction/graph logic worth fixing before the next benchmark run."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = json.loads(RAW_RESULTS_PATH.read_text(encoding="utf-8"))
    scored = [score_row(r) for r in rows]
    summary = summarize(scored)

    (REPORT_DIR / "report.json").write_text(json.dumps({"summary": summary, "rows": scored}, indent=2), encoding="utf-8")
    (REPORT_DIR / "report.md").write_text(render_report_md(summary, scored), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"\nWrote {REPORT_DIR / 'report.md'} and {REPORT_DIR / 'report.json'}")


if __name__ == "__main__":
    main()
