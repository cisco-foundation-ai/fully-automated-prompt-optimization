# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 75.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.011 |
| summarize_hop1 | 5.084 | 4.495 | 9.571 |
| query_hop2 | 2.773 | 2.375 | 4.911 |
| retrieve_hop2 | 0.591 | 0.068 | 1.574 |
| summarize_hop2 | 5.317 | 4.587 | 9.959 |
| answer | 2.626 | 2.279 | 4.692 |
| **Total** | **16.414** | **15.113** | **27.118** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
