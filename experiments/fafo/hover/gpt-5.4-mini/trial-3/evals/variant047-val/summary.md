# Evaluation Summary

Total cases: 300

## Composite Score
- average: 55.00

## Score Breakdown
- num_found: 2.48
- num_gold: 3.00
- num_missing: 0.52
- partial_recall: 82.78
- recall: 55.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 3.110 | 2.720 | 5.484 |
| query_hop2 | 0.851 | 0.690 | 1.149 |
| retrieve_hop2 | 1.391 | 1.530 | 1.710 |
| summarize_hop2 | 3.513 | 3.107 | 6.525 |
| query_hop3 | 0.870 | 0.714 | 1.216 |
| retrieve_hop3 | 1.389 | 1.518 | 1.695 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **11.128** | **10.523** | **16.305** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 135 |
