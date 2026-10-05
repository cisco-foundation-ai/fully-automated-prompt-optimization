# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 81.44

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.052 | 0.002 | 0.024 |
| summarize_hop1 | 4.941 | 4.156 | 8.670 |
| query_hop2 | 2.091 | 1.709 | 3.868 |
| retrieve_hop2 | 0.493 | 0.002 | 1.626 |
| summarize_hop2 | 3.535 | 3.210 | 6.044 |
| answer | 1.825 | 1.657 | 3.010 |
| **Total** | **12.935** | **11.823** | **20.290** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
