# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.33

## Score Breakdown
- exact_match: 61.33
- f1: 70.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.011 |
| summarize_hop1 | 2.232 | 2.067 | 3.662 |
| query_hop2 | 1.018 | 0.984 | 1.390 |
| retrieve_hop2 | 0.660 | 0.003 | 1.575 |
| summarize_hop2 | 3.730 | 3.619 | 6.424 |
| answer | 1.010 | 0.945 | 1.605 |
| **Total** | **8.673** | **8.314** | **12.642** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 116 |
