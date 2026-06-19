# Evaluation Summary

Total cases: 300

## Composite Score
- average: 27.00

## Score Breakdown
- num_found: 1.97
- num_gold: 3.00
- partial_recall: 65.56
- recall: 27.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.010 |
| summarize_hop1 | 3.604 | 3.098 | 5.384 |
| query_hop2 | 0.765 | 0.562 | 1.483 |
| retrieve_hop2 | 0.177 | 0.002 | 1.272 |
| summarize_hop2 | 3.644 | 3.296 | 5.675 |
| query_hop3 | 0.862 | 0.575 | 1.199 |
| retrieve_hop3 | 0.574 | 0.002 | 1.492 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.646** | **8.591** | **15.988** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 219 |
