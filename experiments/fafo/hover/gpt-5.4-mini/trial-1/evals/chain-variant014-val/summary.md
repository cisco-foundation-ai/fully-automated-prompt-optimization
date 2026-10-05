# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- partial_recall: 89.11
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.005 |
| summarize_hop1 | 2.434 | 2.099 | 3.705 |
| query_hop2 | 0.837 | 0.722 | 1.243 |
| retrieve_hop2 | 1.273 | 1.480 | 1.632 |
| summarize_hop2 | 1.663 | 1.478 | 2.482 |
| query_hop3 | 0.693 | 0.593 | 1.054 |
| retrieve_hop3 | 0.279 | 0.002 | 1.560 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.197** | **6.554** | **10.627** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 83 |
