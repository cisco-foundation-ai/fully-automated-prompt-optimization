# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.84

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.009 |
| summarize_hop1 | 5.149 | 4.252 | 9.495 |
| query_hop2 | 2.626 | 2.407 | 4.458 |
| retrieve_hop2 | 0.662 | 0.075 | 1.571 |
| summarize_hop2 | 5.664 | 4.841 | 11.756 |
| answer | 2.733 | 2.438 | 4.528 |
| **Total** | **16.861** | **15.874** | **29.204** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
