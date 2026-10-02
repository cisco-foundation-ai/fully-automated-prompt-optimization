# Evaluation Summary

Total cases: 150

## Composite Score
- average: 65.33

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- num_missing: 0.37
- partial_recall: 87.78
- recall: 65.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.004 | 0.010 |
| summarize_hop1 | 9.114 | 8.950 | 11.943 |
| query_hop2 | 0.385 | 0.309 | 0.846 |
| retrieve_hop2 | 1.031 | 1.261 | 1.637 |
| summarize_hop2 | 8.591 | 8.248 | 15.247 |
| query_hop3 | 0.358 | 0.306 | 0.759 |
| retrieve_hop3 | 1.105 | 1.390 | 1.643 |
| combine_retrievals | 0.005 | 0.005 | 0.007 |
| **Total** | **20.594** | **20.556** | **29.495** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 49 |
| query_hop3 | 3 |
