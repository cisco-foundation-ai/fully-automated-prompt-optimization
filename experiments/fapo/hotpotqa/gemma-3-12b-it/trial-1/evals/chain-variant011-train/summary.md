# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.25

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.003 | 0.012 |
| summarize_hop1 | 2.405 | 2.260 | 4.117 |
| query_hop2 | 1.064 | 1.002 | 1.469 |
| retrieve_hop2 | 0.775 | 0.007 | 1.355 |
| summarize_hop2 | 2.548 | 2.454 | 3.800 |
| answer | 1.074 | 1.006 | 1.585 |
| **Total** | **7.898** | **7.297** | **12.890** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
