# Evaluation Summary

Total cases: 300

## Composite Score
- average: 84.67

## Score Breakdown
- num_found: 2.83
- num_gold: 3.00
- num_missing: 0.17
- partial_recall: 94.22
- recall: 84.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.133 | 1.268 | 1.679 |
| summarize_hop1 | 3.252 | 2.825 | 6.637 |
| query_hop2 | 0.401 | 0.327 | 0.747 |
| retrieve_hop2 | 0.843 | 1.254 | 1.613 |
| summarize_hop2 | 6.847 | 5.937 | 10.069 |
| query_hop3 | 0.432 | 0.381 | 0.637 |
| retrieve_hop3 | 1.851 | 1.590 | 3.155 |
| summarize_hop3 | 8.155 | 6.350 | 11.407 |
| query_hop4 | 0.487 | 0.407 | 0.920 |
| retrieve_hop4 | 1.358 | 1.462 | 1.659 |
| query_hop5 | 0.563 | 0.454 | 1.175 |
| retrieve_hop5 | 2.375 | 2.648 | 3.212 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **27.698** | **24.652** | **35.464** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 46 |
