# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.00

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.33
- recall: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.561 | 2.788 | 8.156 |
| query_hop2 | 0.403 | 0.318 | 0.889 |
| retrieve_hop2 | 0.400 | 0.004 | 1.564 |
| summarize_hop2 | 6.435 | 5.869 | 10.089 |
| query_hop3 | 0.396 | 0.339 | 0.602 |
| retrieve_hop3 | 0.904 | 1.239 | 1.625 |
| summarize_hop3 | 7.820 | 6.931 | 12.960 |
| query_hop4 | 0.548 | 0.425 | 1.266 |
| retrieve_hop4 | 1.374 | 1.530 | 1.646 |
| query_hop5 | 0.571 | 0.486 | 0.909 |
| retrieve_hop5 | 2.662 | 2.940 | 3.229 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.079** | **23.413** | **34.686** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 72 |
