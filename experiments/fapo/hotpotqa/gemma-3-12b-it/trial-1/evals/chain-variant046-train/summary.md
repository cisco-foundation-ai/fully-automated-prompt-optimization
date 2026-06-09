# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.058 | 0.002 | 0.032 |
| summarize_hop1 | 2.461 | 2.220 | 4.044 |
| query_hop2 | 1.036 | 0.980 | 1.505 |
| retrieve_hop2 | 0.376 | 0.002 | 1.298 |
| summarize_hop2 | 2.584 | 2.473 | 4.048 |
| answer | 1.093 | 0.992 | 1.674 |
| **Total** | **7.608** | **7.086** | **11.173** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
