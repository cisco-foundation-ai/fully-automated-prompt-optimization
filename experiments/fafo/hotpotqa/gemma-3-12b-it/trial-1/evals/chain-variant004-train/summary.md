# Evaluation Summary

Total cases: 150

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 72.09

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.081 | 0.003 | 0.061 |
| summarize_hop1 | 2.262 | 2.071 | 3.856 |
| query_hop2 | 1.034 | 0.980 | 1.430 |
| retrieve_hop2 | 1.185 | 1.517 | 1.724 |
| summarize_hop2 | 2.519 | 2.458 | 3.844 |
| answer | 0.930 | 0.907 | 1.326 |
| **Total** | **8.011** | **7.499** | **11.682** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 56 |
