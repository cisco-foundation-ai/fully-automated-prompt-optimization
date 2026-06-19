# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 79.05

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.008 |
| summarize_hop1 | 6.142 | 5.162 | 12.070 |
| query_hop2 | 2.757 | 2.413 | 5.217 |
| retrieve_hop2 | 0.649 | 0.084 | 1.627 |
| summarize_hop2 | 4.324 | 3.757 | 7.834 |
| answer | 2.691 | 2.216 | 5.504 |
| **Total** | **16.589** | **15.184** | **29.103** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
