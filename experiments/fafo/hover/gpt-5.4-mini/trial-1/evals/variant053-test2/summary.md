# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.00

## Score Breakdown
- num_found: 2.75
- num_gold: 3.00
- partial_recall: 91.67
- recall: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.893 | 2.816 | 6.350 |
| query_hop2 | 1.061 | 0.871 | 1.967 |
| retrieve_hop2 | 1.350 | 1.276 | 1.609 |
| summarize_hop2 | 4.951 | 4.240 | 8.963 |
| query_hop3 | 1.431 | 1.015 | 3.357 |
| retrieve_hop3 | 0.909 | 1.055 | 1.588 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.598** | **12.044** | **22.298** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 63 |
