# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.052 | 0.002 | 0.044 |
| summarize_hop1 | 2.320 | 2.054 | 3.893 |
| query_hop2 | 1.298 | 1.212 | 1.995 |
| retrieve_hop2 | 0.597 | 0.002 | 1.631 |
| summarize_hop2 | 2.055 | 1.903 | 3.326 |
| answer | 1.043 | 1.026 | 1.489 |
| **Total** | **7.364** | **6.960** | **11.092** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
