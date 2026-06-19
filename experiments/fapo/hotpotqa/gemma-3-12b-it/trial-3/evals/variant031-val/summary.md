# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.00

## Score Breakdown
- exact_match: 61.00
- f1: 69.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.012 |
| summarize_hop1 | 2.208 | 2.020 | 3.758 |
| query_hop2 | 1.033 | 0.992 | 1.428 |
| retrieve_hop2 | 0.381 | 0.003 | 1.124 |
| summarize_hop2 | 3.641 | 3.505 | 6.357 |
| answer | 1.081 | 1.000 | 1.808 |
| **Total** | **8.383** | **8.043** | **12.546** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 117 |
