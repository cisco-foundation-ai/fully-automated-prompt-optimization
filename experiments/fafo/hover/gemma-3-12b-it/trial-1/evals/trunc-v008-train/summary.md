# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- num_missing: 0.31
- partial_recall: 89.56
- recall: 70.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.006 | 0.004 | 0.012 |
| summarize_hop1 | 3.743 | 3.162 | 8.620 |
| query_hop2 | 0.374 | 0.297 | 0.770 |
| retrieve_hop2 | 1.670 | 1.552 | 1.667 |
| summarize_hop2 | 2.578 | 1.942 | 5.630 |
| query_hop3 | 0.338 | 0.286 | 0.712 |
| retrieve_hop3 | 1.351 | 1.560 | 1.671 |
| combine_retrievals | 0.005 | 0.005 | 0.007 |
| **Total** | **10.066** | **9.130** | **19.811** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 45 |
