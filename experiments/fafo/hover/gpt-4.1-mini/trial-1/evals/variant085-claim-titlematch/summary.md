# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- partial_recall: 88.22
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 2.541 | 2.123 | 6.009 |
| summarize_hop1 | 6.625 | 4.516 | 18.516 |
| query_hop2 | 1.045 | 0.840 | 1.825 |
| retrieve_hop2 | 3.984 | 1.749 | 14.373 |
| summarize_hop2 | 5.819 | 4.532 | 12.630 |
| query_hop3 | 1.229 | 0.990 | 2.267 |
| retrieve_hop3 | 11.575 | 9.730 | 26.128 |
| retrieve_mining | 0.201 | 0.045 | 1.565 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **33.020** | **30.904** | **59.611** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 83 |
