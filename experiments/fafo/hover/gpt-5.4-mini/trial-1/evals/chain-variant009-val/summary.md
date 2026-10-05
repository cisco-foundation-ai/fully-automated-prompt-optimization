# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- partial_recall: 89.00
- recall: 72.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 2.369 | 2.145 | 3.432 |
| query_hop2 | 0.957 | 0.756 | 1.097 |
| retrieve_hop2 | 1.597 | 1.421 | 1.651 |
| summarize_hop2 | 1.876 | 1.736 | 2.684 |
| query_hop3 | 0.706 | 0.626 | 0.983 |
| retrieve_hop3 | 0.198 | 0.002 | 1.532 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.707** | **6.986** | **10.951** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 84 |
