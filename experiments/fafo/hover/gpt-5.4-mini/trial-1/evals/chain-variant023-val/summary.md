# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- partial_recall: 90.67
- recall: 77.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 2.425 | 2.177 | 3.856 |
| query_hop2 | 0.776 | 0.685 | 1.042 |
| retrieve_hop2 | 0.967 | 1.285 | 1.633 |
| summarize_hop2 | 3.161 | 2.913 | 4.870 |
| query_hop3 | 1.059 | 0.812 | 1.357 |
| retrieve_hop3 | 1.304 | 1.345 | 1.642 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.694** | **9.110** | **12.806** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 68 |
