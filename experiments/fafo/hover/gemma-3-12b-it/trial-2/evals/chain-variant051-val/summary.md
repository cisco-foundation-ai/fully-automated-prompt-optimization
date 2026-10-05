# Evaluation Summary

Total cases: 300

## Composite Score
- average: 82.67

## Score Breakdown
- num_found: 2.81
- num_gold: 3.00
- num_missing: 0.19
- partial_recall: 93.56
- recall: 82.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.012 |
| summarize_hop1 | 3.137 | 2.757 | 5.883 |
| query_hop2 | 0.400 | 0.327 | 0.799 |
| retrieve_hop2 | 0.551 | 0.002 | 1.560 |
| summarize_hop2 | 6.345 | 6.001 | 9.932 |
| query_hop3 | 0.431 | 0.380 | 0.614 |
| retrieve_hop3 | 1.467 | 1.469 | 3.064 |
| summarize_hop3 | 6.717 | 6.575 | 10.886 |
| query_hop4 | 0.508 | 0.423 | 0.934 |
| retrieve_hop4 | 1.286 | 1.482 | 1.627 |
| query_hop5 | 0.505 | 0.407 | 1.059 |
| retrieve_hop5 | 2.655 | 2.936 | 3.175 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.006** | **23.966** | **32.478** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 52 |
