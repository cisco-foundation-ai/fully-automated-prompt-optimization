# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.289 | 1.124 | 1.705 |
| summarize_hop1 | 2.340 | 1.990 | 4.404 |
| query_hop2 | 1.010 | 0.962 | 1.437 |
| retrieve_hop2 | 1.162 | 1.316 | 1.619 |
| summarize_hop2 | 1.980 | 1.911 | 2.972 |
| answer | 1.007 | 0.962 | 1.439 |
| **Total** | **8.788** | **8.260** | **11.905** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
