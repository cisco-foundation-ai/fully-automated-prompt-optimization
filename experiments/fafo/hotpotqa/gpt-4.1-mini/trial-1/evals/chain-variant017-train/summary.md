# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 78.10

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.044 | 0.003 | 0.014 |
| summarize_hop1 | 3.154 | 2.660 | 5.624 |
| query_hop2 | 1.677 | 1.531 | 2.749 |
| retrieve_hop2 | 0.455 | 0.003 | 1.098 |
| summarize_hop2 | 2.868 | 2.619 | 5.060 |
| answer | 1.525 | 1.431 | 2.696 |
| **Total** | **9.723** | **8.890** | **13.783** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
