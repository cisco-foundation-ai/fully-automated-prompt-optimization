# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 79.62

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.036 | 0.002 | 0.019 |
| summarize_hop1 | 4.801 | 4.183 | 10.360 |
| query_hop2 | 2.272 | 2.075 | 4.019 |
| retrieve_hop2 | 0.560 | 0.077 | 1.632 |
| summarize_hop2 | 5.561 | 5.038 | 10.006 |
| answer | 2.036 | 1.863 | 3.346 |
| **Total** | **15.266** | **14.279** | **24.830** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
