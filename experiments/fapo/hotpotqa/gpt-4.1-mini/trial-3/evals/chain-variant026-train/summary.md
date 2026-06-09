# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.049 | 0.002 | 0.024 |
| summarize_hop1 | 6.209 | 5.395 | 12.041 |
| query_hop2 | 2.868 | 2.507 | 4.675 |
| retrieve_hop2 | 0.573 | 0.067 | 1.667 |
| summarize_hop2 | 4.532 | 4.066 | 8.929 |
| answer | 2.144 | 1.675 | 5.697 |
| **Total** | **16.375** | **14.812** | **29.115** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
