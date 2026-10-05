# Evaluation Summary

Total cases: 300

## Composite Score
- average: 82.00

## Score Breakdown
- num_found: 2.79
- num_gold: 3.00
- num_missing: 0.21
- partial_recall: 93.00
- recall: 82.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.011 |
| summarize_hop1 | 3.119 | 2.712 | 5.878 |
| query_hop2 | 0.374 | 0.328 | 0.502 |
| retrieve_hop2 | 0.607 | 0.002 | 1.575 |
| summarize_hop2 | 6.374 | 6.073 | 9.525 |
| query_hop3 | 0.425 | 0.379 | 0.661 |
| retrieve_hop3 | 1.548 | 1.446 | 3.075 |
| summarize_hop3 | 6.574 | 6.385 | 10.888 |
| query_hop4 | 0.392 | 0.336 | 0.561 |
| retrieve_hop4 | 1.228 | 1.332 | 1.601 |
| query_hop5 | 0.554 | 0.452 | 1.066 |
| retrieve_hop5 | 1.961 | 1.612 | 3.126 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.160** | **23.063** | **30.460** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 54 |
