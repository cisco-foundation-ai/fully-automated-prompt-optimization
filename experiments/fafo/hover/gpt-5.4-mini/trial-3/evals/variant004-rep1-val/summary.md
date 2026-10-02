# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.00

## Score Breakdown
- num_found: 1.84
- num_gold: 3.00
- num_missing: 1.16
- partial_recall: 61.33
- recall: 23.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.004 |
| summarize_hop1 | 1.663 | 1.506 | 2.545 |
| query_hop2 | 0.978 | 0.762 | 1.342 |
| retrieve_hop2 | 1.247 | 1.076 | 1.621 |
| summarize_hop2 | 1.975 | 1.800 | 2.630 |
| query_hop3 | 0.884 | 0.748 | 1.076 |
| retrieve_hop3 | 1.023 | 1.077 | 1.615 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.780** | **7.210** | **13.119** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 231 |
