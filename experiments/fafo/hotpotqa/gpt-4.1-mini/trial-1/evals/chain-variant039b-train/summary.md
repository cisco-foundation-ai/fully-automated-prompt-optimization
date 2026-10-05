# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 80.79

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.057 | 0.002 | 0.042 |
| summarize_hop1 | 3.941 | 3.356 | 7.831 |
| query_hop2 | 2.002 | 1.612 | 3.666 |
| retrieve_hop2 | 0.372 | 0.002 | 1.561 |
| summarize_hop2 | 3.030 | 2.751 | 5.091 |
| answer | 1.786 | 1.546 | 2.883 |
| **Total** | **11.187** | **10.162** | **18.074** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
