# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.00

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- partial_recall: 89.89
- recall: 75.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 2.419 | 2.303 | 3.932 |
| query_hop2 | 0.728 | 0.685 | 0.982 |
| retrieve_hop2 | 0.747 | 0.002 | 1.633 |
| summarize_hop2 | 3.670 | 3.284 | 6.468 |
| query_hop3 | 0.843 | 0.685 | 1.437 |
| retrieve_hop3 | 0.169 | 0.002 | 1.579 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.580** | **8.019** | **12.721** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 75 |
