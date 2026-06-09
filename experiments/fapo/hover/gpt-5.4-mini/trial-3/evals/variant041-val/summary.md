# Evaluation Summary

Total cases: 300

## Composite Score
- average: 48.33

## Score Breakdown
- num_found: 2.36
- num_gold: 3.00
- num_missing: 0.64
- partial_recall: 78.78
- recall: 48.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.000 | 0.552 | 1.714 |
| summarize_hop1 | 2.379 | 2.120 | 4.440 |
| query_hop2 | 0.799 | 0.702 | 1.030 |
| retrieve_hop2 | 1.382 | 1.360 | 1.632 |
| summarize_hop2 | 2.758 | 2.363 | 4.723 |
| query_hop3 | 0.824 | 0.692 | 1.065 |
| retrieve_hop3 | 1.364 | 1.362 | 1.647 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.506** | **9.832** | **15.283** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 155 |
