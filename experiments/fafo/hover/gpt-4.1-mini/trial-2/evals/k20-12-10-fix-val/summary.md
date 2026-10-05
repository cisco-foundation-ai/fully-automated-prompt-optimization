# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- num_found: 2.56
- num_gold: 3.00
- partial_recall: 85.44
- recall: 63.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.008 |
| summarize_hop1 | 3.867 | 3.345 | 6.626 |
| query_hop2 | 0.750 | 0.587 | 1.489 |
| retrieve_hop2 | 1.526 | 1.454 | 1.568 |
| summarize_hop2 | 4.377 | 3.542 | 7.197 |
| query_hop3 | 0.819 | 0.609 | 1.135 |
| retrieve_hop3 | 0.435 | 0.002 | 1.530 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.778** | **10.493** | **20.107** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 111 |
