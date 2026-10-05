# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- num_missing: 0.35
- partial_recall: 88.22
- recall: 66.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.085 | 0.004 | 0.566 |
| summarize_hop1 | 4.444 | 3.838 | 9.414 |
| extract_queries_hop2 | 0.000 | 0.000 | 0.000 |
| retrieve_hop2 | 2.034 | 1.585 | 4.728 |
| summarize_hop2 | 3.428 | 2.870 | 7.107 |
| extract_queries_hop3 | 0.000 | 0.000 | 0.000 |
| retrieve_hop3 | 2.277 | 1.600 | 4.845 |
| combine_retrievals | 0.006 | 0.005 | 0.011 |
| **Total** | **12.275** | **10.747** | **24.765** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 51 |
