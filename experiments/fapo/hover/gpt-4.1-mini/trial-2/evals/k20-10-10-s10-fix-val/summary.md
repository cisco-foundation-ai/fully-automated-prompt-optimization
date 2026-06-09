# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.67

## Score Breakdown
- num_found: 2.54
- num_gold: 3.00
- partial_recall: 84.56
- recall: 61.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.010 |
| summarize_hop1 | 4.740 | 2.886 | 13.170 |
| query_hop2 | 1.530 | 0.565 | 4.968 |
| retrieve_hop2 | 0.233 | 0.002 | 1.452 |
| summarize_hop2 | 4.504 | 3.283 | 9.732 |
| query_hop3 | 1.747 | 0.602 | 4.824 |
| retrieve_hop3 | 0.672 | 0.005 | 1.531 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.456** | **9.217** | **42.627** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 115 |
