# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.12

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.009 |
| summarize_hop1 | 2.468 | 2.295 | 4.026 |
| query_hop2 | 1.010 | 0.971 | 1.434 |
| retrieve_hop2 | 0.749 | 0.002 | 1.634 |
| summarize_hop2 | 2.266 | 2.158 | 3.480 |
| answer | 1.020 | 1.003 | 1.455 |
| **Total** | **7.543** | **6.899** | **10.947** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
