# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.71

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.089 | 0.002 | 0.066 |
| summarize_hop1 | 1.999 | 1.909 | 2.820 |
| query_hop2 | 1.116 | 1.048 | 1.784 |
| retrieve_hop2 | 0.564 | 0.003 | 1.677 |
| summarize_hop2 | 1.627 | 1.462 | 2.158 |
| answer | 0.841 | 0.804 | 1.155 |
| **Total** | **6.237** | **5.771** | **8.516** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
