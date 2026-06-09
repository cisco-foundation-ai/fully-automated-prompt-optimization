# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.87

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.008 |
| summarize_hop1 | 4.696 | 3.923 | 9.317 |
| query_hop2 | 1.789 | 1.611 | 2.918 |
| retrieve_hop2 | 0.731 | 0.079 | 1.652 |
| summarize_hop2 | 2.432 | 2.256 | 3.736 |
| answer | 1.135 | 0.994 | 1.989 |
| **Total** | **10.799** | **9.645** | **18.502** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
