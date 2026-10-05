# Evaluation Summary

Total cases: 300

## Composite Score
- average: 22.00

## Score Breakdown
- num_found: 1.85
- num_gold: 3.00
- num_missing: 1.15
- partial_recall: 61.78
- recall: 22.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.005 |
| summarize_hop1 | 1.690 | 1.510 | 2.411 |
| query_hop2 | 0.800 | 0.726 | 0.998 |
| retrieve_hop2 | 1.044 | 1.327 | 1.650 |
| summarize_hop2 | 1.922 | 1.806 | 2.628 |
| query_hop3 | 0.939 | 0.762 | 1.143 |
| retrieve_hop3 | 1.299 | 1.461 | 1.662 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.702** | **7.402** | **11.120** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 234 |
