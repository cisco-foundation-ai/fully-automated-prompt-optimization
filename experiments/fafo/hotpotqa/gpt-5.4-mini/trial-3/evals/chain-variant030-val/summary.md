# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.19

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.049 | 0.002 | 0.009 |
| summarize_hop1 | 1.317 | 1.256 | 1.906 |
| query_hop2 | 1.068 | 1.023 | 1.523 |
| retrieve_hop2 | 0.381 | 0.002 | 1.577 |
| summarize_hop2 | 1.354 | 1.269 | 1.973 |
| answer | 0.992 | 0.919 | 1.430 |
| **Total** | **5.162** | **4.665** | **7.052** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
