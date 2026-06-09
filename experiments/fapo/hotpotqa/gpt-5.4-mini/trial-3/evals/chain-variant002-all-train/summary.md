# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.010 |
| summarize_hop1 | 1.525 | 1.449 | 2.119 |
| query_hop2 | 1.176 | 1.091 | 1.896 |
| retrieve_hop2 | 1.551 | 1.375 | 1.730 |
| summarize_hop2 | 1.284 | 1.223 | 1.705 |
| answer | 0.814 | 0.766 | 1.228 |
| **Total** | **6.366** | **6.025** | **7.458** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
