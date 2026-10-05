# Evaluation Summary

Total cases: 300

## Composite Score
- average: 83.00

## Score Breakdown
- num_found: 2.81
- num_gold: 3.00
- num_missing: 0.19
- partial_recall: 93.67
- recall: 83.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.164 | 2.738 | 5.832 |
| query_hop2 | 0.419 | 0.327 | 1.012 |
| retrieve_hop2 | 0.929 | 1.138 | 1.603 |
| summarize_hop2 | 6.418 | 6.083 | 10.662 |
| query_hop3 | 0.463 | 0.380 | 0.884 |
| retrieve_hop3 | 1.502 | 1.477 | 3.107 |
| summarize_hop3 | 6.746 | 6.389 | 11.703 |
| query_hop4 | 0.478 | 0.412 | 0.650 |
| retrieve_hop4 | 1.336 | 1.471 | 1.634 |
| query_hop5 | 0.589 | 0.459 | 1.494 |
| retrieve_hop5 | 2.099 | 1.694 | 3.149 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.147** | **23.675** | **32.798** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 51 |
