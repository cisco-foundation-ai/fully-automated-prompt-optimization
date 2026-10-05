# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.33

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.22
- recall: 79.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 4.073 | 2.763 | 6.993 |
| query_hop2 | 0.422 | 0.342 | 0.643 |
| retrieve_hop2 | 1.792 | 1.554 | 3.130 |
| summarize_hop2 | 6.902 | 5.389 | 8.995 |
| query_hop3 | 0.484 | 0.360 | 1.115 |
| retrieve_hop3 | 1.749 | 1.560 | 3.106 |
| summarize_hop3 | 7.767 | 6.421 | 11.589 |
| query_hop4 | 0.461 | 0.405 | 0.829 |
| retrieve_hop4 | 1.408 | 1.510 | 1.669 |
| query_hop5 | 0.568 | 0.446 | 1.239 |
| retrieve_hop5 | 2.440 | 2.870 | 3.205 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.070** | **24.602** | **35.784** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 62 |
