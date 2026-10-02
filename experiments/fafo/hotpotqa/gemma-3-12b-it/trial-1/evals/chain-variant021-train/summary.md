# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.57

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.017 |
| summarize_hop1 | 2.577 | 2.335 | 4.660 |
| query_hop2 | 1.062 | 1.030 | 1.495 |
| retrieve_hop2 | 0.966 | 0.003 | 1.646 |
| summarize_hop2 | 2.530 | 2.338 | 4.036 |
| answer | 1.084 | 1.052 | 1.457 |
| **Total** | **8.243** | **7.758** | **12.174** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
