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
| retrieve_hop1 | 1.222 | 0.571 | 1.748 |
| summarize_hop1 | 3.927 | 3.288 | 8.820 |
| query_hop2 | 0.316 | 0.288 | 0.492 |
| retrieve_hop2 | 1.409 | 1.530 | 1.634 |
| summarize_hop2 | 3.145 | 2.463 | 8.043 |
| query_hop3 | 0.324 | 0.277 | 0.512 |
| retrieve_hop3 | 1.382 | 1.514 | 1.660 |
| combine_retrievals | 0.005 | 0.005 | 0.008 |
| **Total** | **11.731** | **10.487** | **20.738** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 45 |
