# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.50

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.010 |
| summarize_hop1 | 7.870 | 6.939 | 14.696 |
| query_hop2 | 2.629 | 2.352 | 4.640 |
| retrieve_hop2 | 0.652 | 0.038 | 1.519 |
| summarize_hop2 | 5.036 | 4.359 | 9.234 |
| answer | 2.710 | 2.324 | 6.492 |
| **Total** | **18.915** | **17.882** | **29.818** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
