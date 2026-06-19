# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- partial_recall: 87.44
- recall: 70.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.010 | 0.023 |
| summarize_hop1 | 7.380 | 4.734 | 18.334 |
| query_hop2 | 1.220 | 0.912 | 2.264 |
| retrieve_hop2 | 4.767 | 2.740 | 14.363 |
| summarize_hop2 | 6.573 | 5.107 | 16.417 |
| query_hop3 | 1.352 | 1.028 | 2.459 |
| retrieve_hop3 | 12.562 | 11.223 | 27.369 |
| retrieve_mining | 0.194 | 0.046 | 1.346 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **34.061** | **31.237** | **62.514** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 90 |
