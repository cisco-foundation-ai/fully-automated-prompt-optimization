# Evaluation Summary

Total cases: 150

## Composite Score
- average: 0.00

## Score Breakdown
- num_found: 0.00
- num_gold: 3.00
- num_missing: 3.00
- partial_recall: 0.00
- recall: 0.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.309 | 1.284 | 1.728 |
| summarize_hop1 | 4.189 | 3.601 | 9.804 |
| query_hop2 | 0.333 | 0.289 | 0.592 |
| retrieve_hop2 | 0.442 | 0.005 | 1.529 |
| summarize_hop2 | 3.177 | 2.619 | 7.603 |
| query_hop3 | 0.302 | 0.281 | 0.410 |
| retrieve_hop3 | 0.651 | 0.008 | 1.592 |
| summarize_hop3 | 2.539 | 1.904 | 6.218 |
| query_hop4 | 0.307 | 0.282 | 0.446 |
| retrieve_hop4 | 0.900 | 1.319 | 1.602 |
| **Total** | **14.149** | **12.947** | **27.320** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 150 |
