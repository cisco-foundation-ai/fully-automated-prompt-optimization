# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.33

## Score Breakdown
- exact_match: 62.33
- f1: 69.49

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.010 |
| summarize_hop1 | 2.344 | 2.228 | 3.863 |
| query_hop2 | 1.037 | 1.007 | 1.394 |
| retrieve_hop2 | 0.594 | 0.003 | 1.630 |
| summarize_hop2 | 2.210 | 2.079 | 3.376 |
| answer | 1.018 | 0.965 | 1.519 |
| **Total** | **7.236** | **6.947** | **10.462** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 113 |
