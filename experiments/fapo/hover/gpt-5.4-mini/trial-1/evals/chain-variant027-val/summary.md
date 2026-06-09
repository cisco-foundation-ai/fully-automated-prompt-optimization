# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.00

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- partial_recall: 90.67
- recall: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.005 |
| summarize_hop1 | 2.307 | 2.090 | 3.979 |
| query_hop2 | 0.894 | 0.690 | 1.202 |
| retrieve_hop2 | 0.840 | 1.079 | 1.639 |
| summarize_hop2 | 3.479 | 3.062 | 6.276 |
| query_hop3 | 0.856 | 0.722 | 1.256 |
| retrieve_hop3 | 1.054 | 1.310 | 1.667 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.438** | **8.922** | **14.458** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 72 |
