# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.33

## Score Breakdown
- num_found: 2.75
- num_gold: 3.00
- partial_recall: 91.56
- recall: 77.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.010 |
| summarize_hop1 | 2.603 | 2.371 | 4.264 |
| query_hop2 | 0.982 | 0.790 | 1.712 |
| retrieve_hop2 | 1.061 | 1.445 | 1.603 |
| summarize_hop2 | 4.008 | 3.408 | 6.707 |
| query_hop3 | 1.186 | 0.858 | 1.952 |
| retrieve_hop3 | 0.531 | 0.002 | 1.596 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.390** | **9.727** | **15.526** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 68 |
