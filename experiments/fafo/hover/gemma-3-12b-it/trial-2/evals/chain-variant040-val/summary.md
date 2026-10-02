# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.00

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.22
- recall: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.619 | 3.050 | 7.008 |
| query_hop2 | 0.455 | 0.371 | 0.990 |
| retrieve_hop2 | 2.462 | 2.542 | 3.187 |
| summarize_hop2 | 5.552 | 5.247 | 9.400 |
| query_hop3 | 0.576 | 0.381 | 1.765 |
| retrieve_hop3 | 2.042 | 2.101 | 3.156 |
| summarize_hop3 | 7.394 | 6.867 | 12.751 |
| query_hop4 | 0.612 | 0.420 | 1.844 |
| retrieve_hop4 | 1.353 | 1.493 | 1.648 |
| query_hop5 | 0.608 | 0.461 | 1.485 |
| retrieve_hop5 | 2.091 | 1.872 | 3.182 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.767** | **25.694** | **37.054** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 63 |
