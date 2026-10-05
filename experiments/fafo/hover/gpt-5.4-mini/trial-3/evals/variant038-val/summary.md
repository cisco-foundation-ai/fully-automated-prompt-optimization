# Evaluation Summary

Total cases: 300

## Composite Score
- average: 39.00

## Score Breakdown
- num_found: 2.23
- num_gold: 3.00
- num_missing: 0.77
- partial_recall: 74.22
- recall: 39.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.994 | 0.589 | 1.722 |
| summarize_hop1 | 1.925 | 1.695 | 2.685 |
| query_hop2 | 0.726 | 0.679 | 0.991 |
| retrieve_hop2 | 1.379 | 1.471 | 1.668 |
| summarize_hop2 | 2.183 | 2.056 | 3.442 |
| query_hop3 | 0.811 | 0.668 | 1.068 |
| retrieve_hop3 | 1.349 | 1.473 | 1.652 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.368** | **8.940** | **12.003** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 183 |
