# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.44
- recall: 72.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.354 | 1.335 | 1.720 |
| summarize_hop1 | 4.052 | 3.436 | 10.016 |
| query_hop2 | 0.332 | 0.295 | 0.611 |
| retrieve_hop2 | 0.259 | 0.004 | 1.512 |
| summarize_hop2 | 2.927 | 2.361 | 6.382 |
| query_hop3 | 0.342 | 0.286 | 0.751 |
| retrieve_hop3 | 0.300 | 0.004 | 1.533 |
| summarize_hop3 | 2.519 | 1.865 | 5.980 |
| query_hop4 | 0.325 | 0.279 | 0.600 |
| retrieve_hop4 | 0.301 | 0.005 | 1.513 |
| summarize_hop4 | 2.331 | 1.718 | 5.193 |
| query_hop5 | 0.329 | 0.283 | 0.701 |
| retrieve_hop5 | 0.381 | 0.005 | 1.526 |
| summarize_hop5 | 2.119 | 1.540 | 5.615 |
| query_hop6 | 0.338 | 0.284 | 0.665 |
| retrieve_hop6 | 0.339 | 0.005 | 1.537 |
| combine_retrievals | 0.012 | 0.011 | 0.019 |
| **Total** | **18.558** | **17.299** | **33.116** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop6_trunc | 41 |
