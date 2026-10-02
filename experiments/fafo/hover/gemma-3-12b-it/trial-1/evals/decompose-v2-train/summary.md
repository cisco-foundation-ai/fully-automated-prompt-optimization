# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 91.11
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.249 | 3.955 | 8.312 |
| summarize_hop1 | 4.050 | 3.318 | 10.554 |
| query_hop2 | 0.353 | 0.291 | 0.806 |
| retrieve_hop2 | 0.262 | 0.004 | 1.593 |
| summarize_hop2 | 3.146 | 2.318 | 7.540 |
| query_hop3 | 0.356 | 0.288 | 0.743 |
| retrieve_hop3 | 0.526 | 0.005 | 1.642 |
| combine_retrievals | 0.010 | 0.010 | 0.019 |
| **Total** | **12.953** | **11.870** | **25.175** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 39 |
