# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- exact_match: 73.00
- f1: 78.76

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.075 | 0.002 | 0.012 |
| summarize_hop1 | 1.246 | 1.159 | 1.701 |
| query_hop2 | 1.087 | 1.014 | 1.481 |
| retrieve_hop2 | 0.244 | 0.002 | 1.334 |
| summarize_hop2 | 1.335 | 1.232 | 2.051 |
| answer | 0.937 | 0.895 | 1.293 |
| **Total** | **4.923** | **4.590** | **6.937** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 81 |
