# Evaluation Summary

Total cases: 300

## Composite Score
- average: 96.00

## Score Breakdown
- num_found: 2.96
- num_gold: 3.00
- partial_recall: 98.56
- recall: 96.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.215 | 0.012 | 1.612 |
| summarize_hop1 | 32.625 | 26.603 | 68.594 |
| query_hop2 | 1.597 | 1.252 | 2.390 |
| retrieve_hop2 | 7.804 | 7.723 | 12.427 |
| summarize_hop2 | 34.465 | 27.364 | 54.035 |
| query_hop3 | 1.514 | 1.136 | 2.545 |
| retrieve_hop3 | 8.341 | 8.066 | 12.169 |
| summarize_hop3 | 33.515 | 27.506 | 57.809 |
| query_hop4 | 2.078 | 1.590 | 3.666 |
| retrieve_hop4 | 9.639 | 9.397 | 14.501 |
| combine_retrievals | 0.006 | 0.006 | 0.012 |
| **Total** | **131.799** | **118.392** | **205.094** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 12 |
