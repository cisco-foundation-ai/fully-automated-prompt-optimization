# Evaluation Summary

Total cases: 300

## Composite Score
- average: 56.33

## Score Breakdown
- exact_match: 56.33
- f1: 67.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.011 |
| summarize_hop1 | 2.446 | 2.048 | 3.728 |
| query_hop2 | 1.063 | 1.020 | 1.504 |
| retrieve_hop2 | 0.557 | 0.003 | 1.577 |
| summarize_hop2 | 3.743 | 3.579 | 6.018 |
| answer | 0.964 | 0.915 | 1.375 |
| **Total** | **8.802** | **8.347** | **12.864** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 131 |
