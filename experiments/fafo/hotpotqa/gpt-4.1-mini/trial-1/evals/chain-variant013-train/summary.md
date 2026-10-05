# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.81

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.023 |
| summarize_hop1 | 2.588 | 2.319 | 4.506 |
| query_hop2 | 1.936 | 1.504 | 2.801 |
| retrieve_hop2 | 0.574 | 0.002 | 1.595 |
| summarize_hop2 | 2.672 | 2.560 | 4.143 |
| answer | 1.534 | 1.383 | 2.544 |
| **Total** | **9.338** | **8.468** | **13.785** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
