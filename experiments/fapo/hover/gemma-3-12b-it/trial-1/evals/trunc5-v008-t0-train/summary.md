# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 91.11
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.004 | 0.060 |
| summarize_hop1 | 4.105 | 3.429 | 9.250 |
| query_hop2 | 0.334 | 0.298 | 0.603 |
| retrieve_hop2 | 0.174 | 0.004 | 1.485 |
| summarize_hop2 | 3.058 | 2.421 | 7.135 |
| query_hop3 | 0.348 | 0.284 | 0.768 |
| retrieve_hop3 | 0.413 | 0.004 | 1.575 |
| summarize_hop3 | 2.465 | 1.925 | 5.771 |
| query_hop4 | 0.329 | 0.278 | 0.511 |
| retrieve_hop4 | 0.646 | 0.005 | 1.592 |
| summarize_hop4 | 2.323 | 1.790 | 5.181 |
| query_hop5 | 0.314 | 0.284 | 0.569 |
| retrieve_hop5 | 0.860 | 1.042 | 1.575 |
| combine_retrievals | 0.009 | 0.009 | 0.016 |
| **Total** | **15.390** | **14.079** | **26.354** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5_trunc | 38 |
