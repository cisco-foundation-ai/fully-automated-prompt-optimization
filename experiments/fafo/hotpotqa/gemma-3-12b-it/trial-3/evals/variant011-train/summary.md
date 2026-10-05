# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 73.63

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.040 | 0.002 | 0.022 |
| summarize_hop1 | 2.541 | 2.394 | 4.610 |
| query_hop2 | 0.982 | 0.954 | 1.431 |
| retrieve_hop2 | 0.669 | 0.005 | 1.139 |
| summarize_hop2 | 3.436 | 3.238 | 5.360 |
| answer | 1.050 | 1.006 | 1.571 |
| **Total** | **8.717** | **8.383** | **12.734** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 51 |
