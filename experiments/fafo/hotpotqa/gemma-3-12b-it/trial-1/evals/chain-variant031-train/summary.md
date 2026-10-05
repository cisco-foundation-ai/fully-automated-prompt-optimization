# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 72.56

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.015 |
| summarize_hop1 | 2.449 | 2.327 | 4.205 |
| query_hop2 | 0.989 | 0.940 | 1.383 |
| retrieve_hop2 | 0.923 | 0.008 | 1.624 |
| summarize_hop2 | 2.297 | 2.209 | 3.503 |
| answer | 1.040 | 0.979 | 1.515 |
| **Total** | **7.732** | **7.255** | **11.675** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 50 |
