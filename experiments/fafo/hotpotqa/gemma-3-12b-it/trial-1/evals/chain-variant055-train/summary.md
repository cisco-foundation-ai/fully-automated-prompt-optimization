# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.073 | 0.002 | 0.056 |
| summarize_hop1 | 2.400 | 2.248 | 3.791 |
| query_hop2 | 1.033 | 0.996 | 1.440 |
| retrieve_hop2 | 0.452 | 0.002 | 1.629 |
| summarize_hop2 | 2.287 | 2.136 | 3.842 |
| answer | 0.989 | 0.925 | 1.418 |
| **Total** | **7.233** | **6.632** | **11.687** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
