# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 73.62

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.061 |
| summarize_hop1 | 3.010 | 2.848 | 5.437 |
| query_hop2 | 1.435 | 1.409 | 2.006 |
| retrieve_hop2 | 0.620 | 0.003 | 1.644 |
| summarize_hop2 | 1.971 | 1.902 | 3.045 |
| answer | 1.032 | 1.004 | 1.629 |
| **Total** | **8.110** | **7.452** | **12.351** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 51 |
