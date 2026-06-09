# Evaluation Summary

Total cases: 150

## Composite Score
- average: 88.00

## Score Breakdown
- num_found: 2.88
- num_gold: 3.00
- num_missing: 0.12
- partial_recall: 96.00
- recall: 88.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 6.133 | 5.903 | 11.296 |
| summarize_hop1 | 1.602 | 1.313 | 3.618 |
| retrieve_hop2 | 8.913 | 8.939 | 14.843 |
| summarize_hop2 | 1.334 | 1.160 | 2.351 |
| retrieve_hop3 | 4.412 | 3.359 | 11.382 |
| summarize_hop3 | 1.295 | 1.197 | 2.364 |
| retrieve_hop4 | 2.051 | 1.692 | 5.119 |
| combine_retrievals | 0.052 | 0.046 | 0.117 |
| **Total** | **25.790** | **25.099** | **43.078** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 18 |
