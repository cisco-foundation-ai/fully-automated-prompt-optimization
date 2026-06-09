# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.00

## Score Breakdown
- num_found: 2.53
- num_gold: 3.00
- partial_recall: 84.22
- recall: 60.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.005 |
| summarize_hop1 | 3.101 | 2.827 | 5.241 |
| query_hop2 | 0.737 | 0.560 | 1.396 |
| retrieve_hop2 | 0.895 | 1.214 | 1.504 |
| summarize_hop2 | 3.228 | 2.990 | 5.432 |
| query_hop3 | 0.784 | 0.567 | 1.154 |
| retrieve_hop3 | 1.216 | 1.284 | 1.556 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.970** | **9.497** | **15.637** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 120 |
