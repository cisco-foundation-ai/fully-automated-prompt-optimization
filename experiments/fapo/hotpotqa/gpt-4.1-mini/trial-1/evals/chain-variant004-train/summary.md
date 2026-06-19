# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 77.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.013 | 0.002 | 0.011 |
| summarize_hop1 | 4.355 | 3.814 | 8.713 |
| query_hop2 | 1.975 | 1.728 | 3.492 |
| retrieve_hop2 | 1.098 | 0.554 | 1.763 |
| summarize_hop2 | 3.347 | 2.869 | 6.407 |
| answer | 1.295 | 1.215 | 2.190 |
| **Total** | **12.083** | **11.191** | **20.730** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
