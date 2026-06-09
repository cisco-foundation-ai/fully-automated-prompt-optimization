# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.062 | 0.002 | 0.044 |
| summarize_hop1 | 3.367 | 2.790 | 7.595 |
| query_hop2 | 1.736 | 1.507 | 3.377 |
| retrieve_hop2 | 0.476 | 0.004 | 1.630 |
| summarize_hop2 | 3.208 | 2.976 | 5.131 |
| answer | 2.961 | 2.527 | 5.906 |
| **Total** | **11.810** | **11.206** | **17.939** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
