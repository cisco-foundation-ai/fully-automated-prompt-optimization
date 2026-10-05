# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 90.89
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.004 | 0.024 |
| summarize_hop1 | 3.781 | 3.629 | 6.969 |
| query_hop2 | 0.340 | 0.297 | 0.623 |
| retrieve_hop2 | 0.298 | 0.004 | 1.589 |
| summarize_hop2 | 2.997 | 2.464 | 6.786 |
| query_hop3 | 0.302 | 0.288 | 0.415 |
| retrieve_hop3 | 0.452 | 0.005 | 1.647 |
| summarize_hop3 | 2.574 | 2.062 | 5.801 |
| query_hop4 | 0.344 | 0.292 | 0.698 |
| retrieve_hop4 | 0.473 | 0.005 | 1.611 |
| summarize_hop4 | 2.441 | 1.752 | 5.658 |
| query_hop5 | 0.329 | 0.285 | 0.609 |
| retrieve_hop5 | 0.902 | 1.031 | 1.636 |
| combine_retrievals | 0.009 | 0.009 | 0.015 |
| **Total** | **15.249** | **13.672** | **26.629** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5_trunc | 39 |
