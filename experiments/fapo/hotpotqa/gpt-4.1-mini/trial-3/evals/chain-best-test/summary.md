# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 75.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.097 | 1.347 | 1.676 |
| summarize_hop1 | 5.691 | 4.986 | 10.979 |
| query_hop2 | 2.874 | 2.420 | 5.313 |
| retrieve_hop2 | 0.959 | 1.347 | 1.656 |
| summarize_hop2 | 4.461 | 4.000 | 7.335 |
| answer | 2.446 | 2.042 | 4.443 |
| **Total** | **17.530** | **15.940** | **29.550** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
