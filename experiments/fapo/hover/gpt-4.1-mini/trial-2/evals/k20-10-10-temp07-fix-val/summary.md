# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.00

## Score Breakdown
- num_found: 2.55
- num_gold: 3.00
- partial_recall: 85.11
- recall: 62.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.007 |
| summarize_hop1 | 3.811 | 3.342 | 6.662 |
| query_hop2 | 1.107 | 0.585 | 1.987 |
| retrieve_hop2 | 0.067 | 0.002 | 0.009 |
| summarize_hop2 | 3.828 | 3.444 | 7.245 |
| query_hop3 | 0.780 | 0.605 | 1.119 |
| retrieve_hop3 | 0.366 | 0.002 | 1.240 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.992** | **8.900** | **16.109** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 114 |
