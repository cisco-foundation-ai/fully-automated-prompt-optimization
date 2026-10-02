# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.33

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- partial_recall: 90.89
- recall: 75.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.009 |
| summarize_hop1 | 2.308 | 2.198 | 3.543 |
| query_hop2 | 0.877 | 0.677 | 1.442 |
| retrieve_hop2 | 0.682 | 0.003 | 1.635 |
| summarize_hop2 | 3.449 | 3.151 | 5.812 |
| query_hop3 | 0.820 | 0.701 | 1.418 |
| retrieve_hop3 | 0.583 | 0.002 | 1.602 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.744** | **8.114** | **12.719** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 74 |
