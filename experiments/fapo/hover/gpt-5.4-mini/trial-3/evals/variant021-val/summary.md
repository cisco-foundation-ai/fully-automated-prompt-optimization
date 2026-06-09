# Evaluation Summary

Total cases: 300

## Composite Score
- average: 20.33

## Score Breakdown
- num_found: 1.79
- num_gold: 3.00
- num_missing: 1.21
- partial_recall: 59.56
- recall: 20.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 1.615 | 1.450 | 2.341 |
| query_hop2 | 0.857 | 0.726 | 1.053 |
| retrieve_hop2 | 1.469 | 1.371 | 1.661 |
| summarize_hop2 | 1.805 | 1.756 | 2.442 |
| query_hop3 | 0.904 | 0.728 | 1.055 |
| retrieve_hop3 | 1.325 | 1.345 | 1.646 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.978** | **7.522** | **9.870** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 239 |
