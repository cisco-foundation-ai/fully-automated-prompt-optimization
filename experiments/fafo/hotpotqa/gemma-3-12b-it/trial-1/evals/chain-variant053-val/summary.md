# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 70.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.012 |
| summarize_hop1 | 2.336 | 2.208 | 3.747 |
| query_hop2 | 1.045 | 1.018 | 1.493 |
| retrieve_hop2 | 0.402 | 0.003 | 1.587 |
| summarize_hop2 | 2.618 | 2.534 | 3.892 |
| answer | 0.996 | 0.942 | 1.574 |
| **Total** | **7.436** | **7.250** | **10.619** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
