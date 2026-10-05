# Evaluation Summary

Total cases: 150

## Composite Score
- average: 73.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.67
- recall: 73.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.004 | 0.023 |
| summarize_hop1 | 4.258 | 3.566 | 10.807 |
| query_hop2 | 0.345 | 0.292 | 0.606 |
| retrieve_hop2 | 0.879 | 0.007 | 1.660 |
| summarize_hop2 | 3.241 | 2.463 | 8.590 |
| query_hop3 | 0.327 | 0.280 | 0.682 |
| retrieve_hop3 | 0.702 | 0.005 | 1.655 |
| summarize_hop3 | 2.538 | 1.804 | 6.655 |
| query_hop4 | 0.328 | 0.281 | 0.693 |
| retrieve_hop4 | 1.217 | 1.359 | 1.667 |
| combine_retrievals | 0.007 | 0.007 | 0.011 |
| **Total** | **13.851** | **12.133** | **26.662** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 40 |
