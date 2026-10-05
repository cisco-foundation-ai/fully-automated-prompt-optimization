# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.051 |
| summarize_hop1 | 2.153 | 1.780 | 4.732 |
| query_hop2 | 1.076 | 1.002 | 1.766 |
| retrieve_hop2 | 0.823 | 0.003 | 1.644 |
| summarize_hop2 | 3.652 | 3.363 | 6.666 |
| answer | 1.180 | 1.032 | 2.034 |
| **Total** | **8.922** | **8.308** | **13.777** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
