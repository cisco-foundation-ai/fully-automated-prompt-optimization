# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.33
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.864 | 4.462 | 9.540 |
| summarize_hop1 | 3.942 | 3.258 | 8.801 |
| query_hop2 | 0.327 | 0.288 | 0.506 |
| retrieve_hop2 | 6.365 | 6.483 | 8.107 |
| summarize_hop2 | 3.080 | 2.357 | 6.630 |
| query_hop3 | 0.314 | 0.273 | 0.653 |
| retrieve_hop3 | 6.363 | 6.507 | 8.179 |
| combine_retrievals | 0.027 | 0.026 | 0.043 |
| **Total** | **25.283** | **24.627** | **34.467** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 38 |
