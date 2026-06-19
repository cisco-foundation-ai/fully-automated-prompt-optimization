# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.00

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- partial_recall: 91.22
- recall: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.004 |
| summarize_hop1 | 2.637 | 2.449 | 4.099 |
| query_hop2 | 0.973 | 0.796 | 1.560 |
| retrieve_hop2 | 0.839 | 1.044 | 1.615 |
| summarize_hop2 | 4.145 | 3.537 | 7.380 |
| query_hop3 | 1.107 | 0.886 | 2.284 |
| retrieve_hop3 | 0.410 | 0.002 | 1.549 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.136** | **9.532** | **15.055** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 72 |
