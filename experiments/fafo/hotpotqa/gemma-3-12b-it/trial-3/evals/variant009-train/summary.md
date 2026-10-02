# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.47

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.012 |
| summarize_hop1 | 1.729 | 1.585 | 3.000 |
| query_hop2 | 0.952 | 0.917 | 1.259 |
| retrieve_hop2 | 1.514 | 1.597 | 1.701 |
| summarize_hop2 | 4.645 | 2.485 | 4.228 |
| answer | 1.013 | 0.971 | 1.426 |
| **Total** | **9.868** | **7.270** | **11.341** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
