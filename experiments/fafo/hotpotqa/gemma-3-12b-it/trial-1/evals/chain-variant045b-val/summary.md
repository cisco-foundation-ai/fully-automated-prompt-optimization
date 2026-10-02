# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.00

## Score Breakdown
- exact_match: 65.00
- f1: 72.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.013 |
| summarize_hop1 | 2.360 | 2.183 | 3.952 |
| query_hop2 | 1.051 | 0.987 | 1.585 |
| retrieve_hop2 | 0.503 | 0.002 | 1.580 |
| summarize_hop2 | 2.790 | 2.568 | 4.847 |
| answer | 1.100 | 1.008 | 1.680 |
| **Total** | **7.846** | **7.351** | **11.950** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 105 |
