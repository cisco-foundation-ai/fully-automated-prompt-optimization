# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.67

## Score Breakdown
- num_found: 2.75
- num_gold: 3.00
- num_missing: 0.25
- partial_recall: 91.78
- recall: 77.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.007 |
| summarize_hop1 | 3.021 | 2.684 | 5.768 |
| query_hop2 | 0.385 | 0.323 | 0.691 |
| retrieve_hop2 | 0.552 | 0.002 | 1.555 |
| summarize_hop2 | 6.194 | 5.867 | 9.826 |
| query_hop3 | 0.469 | 0.374 | 0.897 |
| retrieve_hop3 | 1.624 | 1.453 | 3.068 |
| summarize_hop3 | 7.770 | 7.530 | 12.030 |
| query_hop4 | 0.525 | 0.424 | 1.022 |
| retrieve_hop4 | 1.353 | 1.434 | 1.637 |
| query_hop5 | 0.596 | 0.459 | 1.344 |
| retrieve_hop5 | 2.235 | 2.545 | 3.139 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.727** | **24.160** | **33.395** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 67 |
