# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.67

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- partial_recall: 90.67
- recall: 75.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.007 |
| summarize_hop1 | 2.581 | 2.385 | 4.210 |
| query_hop2 | 0.879 | 0.722 | 1.413 |
| retrieve_hop2 | 0.483 | 0.002 | 1.173 |
| summarize_hop2 | 3.664 | 3.213 | 6.362 |
| query_hop3 | 0.855 | 0.734 | 1.438 |
| retrieve_hop3 | 0.223 | 0.002 | 1.074 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.709** | **8.102** | **12.848** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 73 |
