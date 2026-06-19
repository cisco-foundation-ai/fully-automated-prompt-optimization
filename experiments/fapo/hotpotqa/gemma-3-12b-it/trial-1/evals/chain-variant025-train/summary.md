# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.21

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.070 | 0.002 | 0.033 |
| summarize_hop1 | 2.396 | 2.204 | 4.093 |
| query_hop2 | 1.033 | 0.996 | 1.430 |
| retrieve_hop2 | 0.632 | 0.003 | 1.610 |
| summarize_hop2 | 2.612 | 2.518 | 3.801 |
| answer | 1.026 | 1.010 | 1.446 |
| **Total** | **7.769** | **7.416** | **11.274** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
