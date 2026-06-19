# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 75.09

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.048 | 0.002 | 0.049 |
| summarize_hop1 | 1.736 | 1.552 | 3.101 |
| query_hop2 | 0.973 | 0.923 | 1.337 |
| retrieve_hop2 | 0.885 | 0.006 | 1.708 |
| summarize_hop2 | 2.567 | 2.428 | 4.321 |
| answer | 1.006 | 0.960 | 1.445 |
| **Total** | **7.214** | **6.793** | **10.016** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
