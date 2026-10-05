# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.76

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.062 | 0.002 | 0.048 |
| summarize_hop1 | 2.171 | 2.061 | 3.575 |
| query_hop2 | 1.340 | 1.323 | 1.792 |
| retrieve_hop2 | 0.921 | 1.058 | 1.644 |
| summarize_hop2 | 2.093 | 2.002 | 3.058 |
| answer | 0.835 | 0.817 | 1.137 |
| **Total** | **7.423** | **6.986** | **10.539** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
