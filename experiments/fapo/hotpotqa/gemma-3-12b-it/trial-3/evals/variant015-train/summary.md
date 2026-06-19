# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 74.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.090 | 0.002 | 0.047 |
| summarize_hop1 | 2.070 | 1.921 | 3.764 |
| query_hop2 | 0.988 | 0.964 | 1.320 |
| retrieve_hop2 | 0.662 | 0.003 | 1.665 |
| summarize_hop2 | 2.211 | 2.135 | 3.160 |
| answer | 1.012 | 1.000 | 1.410 |
| **Total** | **7.033** | **6.544** | **10.112** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
