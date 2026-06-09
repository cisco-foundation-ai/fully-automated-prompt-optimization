# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- num_found: 2.66
- num_gold: 3.00
- num_missing: 0.34
- partial_recall: 88.78
- recall: 69.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.006 | 0.003 | 0.008 |
| summarize_hop1 | 8.578 | 7.954 | 13.462 |
| query_hop2 | 1.050 | 0.802 | 1.834 |
| retrieve_hop2 | 1.616 | 1.418 | 1.648 |
| summarize_hop2 | 4.040 | 3.575 | 7.366 |
| query_hop3 | 1.050 | 0.784 | 2.446 |
| retrieve_hop3 | 1.409 | 1.431 | 1.652 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **17.749** | **16.868** | **25.753** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 93 |
