# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.67

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- partial_recall: 90.44
- recall: 77.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.004 |
| summarize_hop1 | 2.544 | 2.215 | 3.964 |
| query_hop2 | 0.833 | 0.732 | 1.114 |
| retrieve_hop2 | 1.464 | 1.618 | 1.740 |
| summarize_hop2 | 3.743 | 3.343 | 7.223 |
| query_hop3 | 0.939 | 0.760 | 1.757 |
| retrieve_hop3 | 1.116 | 1.526 | 1.696 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.651** | **9.956** | **17.472** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 67 |
