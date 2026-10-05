# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.33

## Score Breakdown
- exact_match: 57.33
- f1: 67.77

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.003 | 0.011 |
| summarize_hop1 | 2.249 | 2.128 | 3.805 |
| query_hop2 | 1.021 | 0.968 | 1.377 |
| retrieve_hop2 | 0.396 | 0.003 | 1.346 |
| summarize_hop2 | 3.329 | 3.144 | 5.546 |
| answer | 1.114 | 1.023 | 1.790 |
| **Total** | **8.140** | **7.843** | **11.406** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 128 |
