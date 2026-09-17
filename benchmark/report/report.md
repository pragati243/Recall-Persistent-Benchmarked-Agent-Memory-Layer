# Recall Benchmark Report

18 probes across 3 categories. Exact-match scoring against hand-written ground truth (see benchmark/dataset/probes.csv).

| Category | N | Recall Accuracy | Correctness Accuracy | False-Memory Rate |
|---|---|---|---|---|
| contradiction | 6 | 100% | 33% | 0% |
| multi_hop | 6 | 100% | 0% | 0% |
| simple_recall | 6 | 100% | 83% | 0% |
| overall | 18 | 100% | 39% | 0% |

## Failures (correctness miss)

- **seq_04** (simple_recall): 'Which city does the user live in?' — expected 'Austin', mode=graph, top hit='Science Fiction (preference)'
- **seq_07** (contradiction): 'How does the user currently want to be notified?' — expected 'SMS', mode=vector, top hit='The user prefers email notifications.'
- **seq_08** (contradiction): 'When does the user prefer to have meetings?' — expected 'afternoon', mode=vector, top hit='The user prefers morning meetings.'
- **seq_09** (contradiction): 'When is the Nimbus project deadline?' — expected 'April 15', mode=vector, top hit='The Nimbus project deadline is set for March 1st.'
- **seq_11** (contradiction): 'What diet does the user currently follow?' — expected 'vegan', mode=vector, top hit='The user follows a vegetarian diet.'
- **seq_13** (multi_hop): 'Who does Raj report to?' — expected 'Sarah', mode=graph, top hit='Atlas (project)'
- **seq_14** (multi_hop): "Who is Tom's manager?" — expected 'Lena', mode=graph, top hit='Falcon team (project)'
- **seq_15** (multi_hop): 'Which office is the Nimbus project associated with?' — expected 'Chicago', mode=graph, top hit='Platform group (project)'
- **seq_16** (multi_hop): "Which library does Omar's project depend on?" — expected 'Aurora', mode=graph, top hit='Comet (project)'
- **seq_17** (multi_hop): 'Which team runs the initiative sponsored by Priya?' — expected 'Growth', mode=graph, top hit='Vega initiative (project)'
- **seq_18** (multi_hop): "Which platform is Jordan's service part of?" — expected 'Payments', mode=graph, top hit='Billing service (project)'

## Interpretation

Weakest category: **multi_hop** at 0% correctness accuracy (n=6). See the failures above for exactly which probes missed and what ranked first instead - that's the starting point for deciding whether it's a routing issue, an extraction-consistency issue, or a real gap in the contradiction/graph logic worth fixing before the next benchmark run.
