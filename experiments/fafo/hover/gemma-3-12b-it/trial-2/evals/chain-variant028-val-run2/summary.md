# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 90.89
- recall: 75.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.011 |
| summarize_hop1 | 4.142 | 3.241 | 9.526 |
| query_hop2 | 0.374 | 0.319 | 0.652 |
| retrieve_hop2 | 0.314 | 0.002 | 1.420 |
| summarize_hop2 | 6.367 | 6.133 | 9.705 |
| query_hop3 | 0.427 | 0.345 | 0.906 |
| retrieve_hop3 | 1.068 | 1.231 | 1.464 |
| summarize_hop3 | 7.504 | 6.431 | 12.022 |
| query_hop4 | 0.497 | 0.434 | 0.795 |
| retrieve_hop4 | 1.226 | 1.272 | 1.516 |
| query_hop5 | 0.422 | 0.374 | 0.659 |
| retrieve_hop5 | 1.207 | 1.271 | 1.508 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.555** | **22.193** | **33.374** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 75 |
