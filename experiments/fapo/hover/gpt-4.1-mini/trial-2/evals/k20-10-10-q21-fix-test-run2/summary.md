# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- num_found: 2.56
- num_gold: 3.00
- partial_recall: 85.33
- recall: 63.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.013 | 0.002 | 0.005 |
| summarize_hop1 | 5.763 | 4.259 | 9.345 |
| query_hop2 | 1.048 | 0.611 | 2.001 |
| retrieve_hop2 | 0.636 | 0.004 | 1.527 |
| summarize_hop2 | 5.355 | 4.253 | 10.667 |
| query_hop3 | 0.949 | 0.615 | 1.739 |
| retrieve_hop3 | 0.804 | 1.170 | 1.514 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **14.568** | **11.856** | **29.034** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 111 |
