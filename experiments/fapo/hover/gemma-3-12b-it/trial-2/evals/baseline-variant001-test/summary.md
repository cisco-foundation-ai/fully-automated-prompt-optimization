# Evaluation Summary

Total cases: 300

## Composite Score
- average: 17.00

## Score Breakdown
- num_found: 1.73
- num_gold: 3.00
- num_missing: 1.27
- partial_recall: 57.67
- recall: 17.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.092 | 1.103 | 1.704 |
| summarize_hop1 | 0.660 | 0.556 | 0.939 |
| query_hop2 | 1.663 | 0.973 | 6.154 |
| retrieve_hop2 | 0.799 | 1.097 | 1.648 |
| summarize_hop2 | 1.012 | 0.647 | 3.575 |
| query_hop3 | 2.343 | 2.170 | 5.582 |
| retrieve_hop3 | 0.535 | 0.113 | 1.646 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.103** | **7.297** | **13.763** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 249 |
