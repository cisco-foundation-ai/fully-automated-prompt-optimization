# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 80.57

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.047 |
| summarize_hop1 | 3.464 | 3.038 | 6.465 |
| query_hop2 | 1.989 | 1.773 | 3.510 |
| retrieve_hop2 | 0.344 | 0.002 | 1.530 |
| summarize_hop2 | 3.014 | 2.833 | 5.155 |
| answer | 1.560 | 1.472 | 2.347 |
| **Total** | **10.412** | **9.445** | **16.310** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
