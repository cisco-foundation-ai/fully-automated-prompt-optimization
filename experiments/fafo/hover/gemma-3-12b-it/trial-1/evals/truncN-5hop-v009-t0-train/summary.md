# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- num_missing: 0.30
- partial_recall: 90.00
- recall: 71.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.089 | 0.004 | 1.097 |
| summarize_hop1 | 4.398 | 3.560 | 9.979 |
| query_hop2 | 0.364 | 0.308 | 0.766 |
| retrieve_hop2 | 1.064 | 1.249 | 1.626 |
| summarize_hop2 | 4.715 | 2.510 | 8.370 |
| query_hop3 | 0.344 | 0.296 | 0.578 |
| retrieve_hop3 | 1.079 | 1.295 | 1.651 |
| summarize_hop3 | 4.343 | 2.026 | 6.999 |
| query_hop4 | 0.339 | 0.297 | 0.625 |
| retrieve_hop4 | 1.064 | 1.305 | 1.649 |
| summarize_hop4 | 4.035 | 1.857 | 6.110 |
| query_hop5 | 0.324 | 0.300 | 0.505 |
| retrieve_hop5 | 0.910 | 1.289 | 1.656 |
| combine_retrievals | 0.009 | 0.009 | 0.015 |
| **Total** | **23.077** | **17.199** | **31.716** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5_trunc | 43 |
