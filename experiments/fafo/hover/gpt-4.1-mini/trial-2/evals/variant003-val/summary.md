# Evaluation Summary

Total cases: 300

## Composite Score
- average: 22.00

## Score Breakdown
- num_found: 1.82
- num_gold: 3.00
- partial_recall: 60.78
- recall: 22.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.037 | 0.002 | 0.007 |
| summarize_hop1 | 2.217 | 1.958 | 3.815 |
| query_hop2 | 0.700 | 0.532 | 1.093 |
| retrieve_hop2 | 0.456 | 0.002 | 1.651 |
| summarize_hop2 | 2.806 | 2.353 | 5.367 |
| query_hop3 | 0.602 | 0.513 | 0.825 |
| retrieve_hop3 | 0.570 | 0.002 | 1.647 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.389** | **6.527** | **12.974** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 234 |
