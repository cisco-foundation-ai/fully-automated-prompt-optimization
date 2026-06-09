# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 80.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.149 | 0.002 | 2.124 |
| summarize_hop1 | 1.249 | 1.183 | 1.730 |
| query_hop2 | 1.169 | 1.051 | 2.061 |
| retrieve_hop2 | 0.481 | 0.002 | 1.620 |
| summarize_hop2 | 1.338 | 1.280 | 1.797 |
| answer | 0.978 | 0.922 | 1.446 |
| **Total** | **5.364** | **4.985** | **7.177** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
