# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 72.71

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.057 | 0.003 | 0.049 |
| summarize_hop1 | 2.282 | 2.104 | 3.769 |
| query_hop2 | 1.247 | 1.200 | 1.786 |
| retrieve_hop2 | 0.679 | 0.003 | 1.650 |
| summarize_hop2 | 2.331 | 2.211 | 3.669 |
| answer | 1.049 | 1.031 | 1.523 |
| **Total** | **7.645** | **7.159** | **11.054** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
