# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- num_found: 2.64
- num_gold: 3.00
- num_missing: 0.36
- partial_recall: 88.00
- recall: 66.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.066 | 0.004 | 0.180 |
| summarize_hop1 | 9.904 | 8.552 | 20.369 |
| query_hop2 | 0.348 | 0.300 | 0.616 |
| retrieve_hop2 | 1.753 | 1.539 | 1.677 |
| summarize_hop2 | 10.531 | 7.953 | 21.494 |
| query_hop3 | 0.354 | 0.298 | 0.617 |
| retrieve_hop3 | 1.429 | 1.578 | 1.689 |
| combine_retrievals | 0.005 | 0.005 | 0.008 |
| **Total** | **24.389** | **20.037** | **47.115** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 51 |
