# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.33

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- partial_recall: 89.89
- recall: 74.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.010 |
| summarize_hop1 | 2.270 | 2.118 | 3.563 |
| query_hop2 | 0.866 | 0.660 | 1.099 |
| retrieve_hop2 | 0.609 | 0.002 | 1.646 |
| summarize_hop2 | 3.341 | 2.995 | 5.370 |
| query_hop3 | 0.961 | 0.694 | 1.296 |
| retrieve_hop3 | 0.381 | 0.002 | 1.593 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.448** | **7.745** | **12.261** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 77 |
