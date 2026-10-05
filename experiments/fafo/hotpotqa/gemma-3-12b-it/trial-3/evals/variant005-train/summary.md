# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 74.83

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.054 | 0.002 | 0.035 |
| summarize_hop1 | 1.771 | 1.606 | 3.301 |
| query_hop2 | 0.973 | 0.956 | 1.281 |
| retrieve_hop2 | 1.131 | 1.325 | 1.637 |
| summarize_hop2 | 2.570 | 2.414 | 4.359 |
| answer | 1.059 | 1.048 | 1.478 |
| **Total** | **7.559** | **7.086** | **10.018** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
