# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 4.483 | 4.090 | 7.463 |
| query_hop2 | 2.091 | 1.973 | 3.563 |
| retrieve_hop2 | 1.687 | 1.394 | 1.738 |
| summarize_hop2 | 5.647 | 4.601 | 11.801 |
| answer | 1.803 | 1.701 | 2.753 |
| **Total** | **15.715** | **14.326** | **27.772** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
