# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 74.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.010 |
| summarize_hop1 | 3.949 | 2.978 | 7.023 |
| query_hop2 | 2.084 | 1.885 | 3.922 |
| retrieve_hop2 | 0.837 | 0.091 | 1.675 |
| summarize_hop2 | 3.762 | 3.193 | 7.127 |
| answer | 1.622 | 1.493 | 2.810 |
| **Total** | **12.272** | **10.864** | **21.712** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
