# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- num_found: 2.64
- num_gold: 3.00
- num_missing: 0.36
- partial_recall: 88.11
- recall: 68.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.326 | 2.718 | 7.106 |
| query_hop2 | 0.378 | 0.332 | 0.704 |
| retrieve_hop2 | 0.482 | 0.002 | 1.639 |
| summarize_hop2 | 9.370 | 7.489 | 13.994 |
| query_hop3 | 0.374 | 0.342 | 0.613 |
| retrieve_hop3 | 0.525 | 0.002 | 1.648 |
| summarize_hop3 | 9.058 | 7.364 | 13.928 |
| query_hop4 | 0.490 | 0.439 | 0.848 |
| retrieve_hop4 | 1.479 | 1.581 | 1.695 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **25.485** | **21.941** | **34.956** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 95 |
