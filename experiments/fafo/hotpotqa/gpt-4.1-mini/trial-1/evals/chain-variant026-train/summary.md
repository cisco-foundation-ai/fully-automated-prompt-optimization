# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.56

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.028 |
| summarize_hop1 | 3.438 | 3.062 | 5.374 |
| query_hop2 | 1.660 | 1.453 | 3.179 |
| retrieve_hop2 | 0.597 | 0.002 | 1.595 |
| summarize_hop2 | 2.728 | 2.503 | 3.991 |
| answer | 1.540 | 1.430 | 2.354 |
| **Total** | **10.000** | **9.140** | **16.657** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
