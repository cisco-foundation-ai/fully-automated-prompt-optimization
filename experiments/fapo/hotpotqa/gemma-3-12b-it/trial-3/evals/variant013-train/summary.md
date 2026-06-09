# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 76.24

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.048 |
| summarize_hop1 | 1.836 | 1.590 | 3.483 |
| query_hop2 | 1.013 | 0.963 | 1.293 |
| retrieve_hop2 | 0.758 | 0.003 | 1.625 |
| summarize_hop2 | 2.664 | 2.559 | 4.509 |
| answer | 0.909 | 0.851 | 1.333 |
| **Total** | **7.220** | **6.514** | **10.338** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
