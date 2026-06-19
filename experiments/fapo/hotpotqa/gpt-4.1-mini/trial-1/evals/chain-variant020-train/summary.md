# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 79.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.043 | 0.002 | 0.036 |
| summarize_hop1 | 2.992 | 2.713 | 4.899 |
| query_hop2 | 1.709 | 1.519 | 2.946 |
| retrieve_hop2 | 0.510 | 0.002 | 1.644 |
| summarize_hop2 | 3.301 | 2.805 | 5.264 |
| answer | 1.770 | 1.613 | 2.602 |
| **Total** | **10.325** | **9.649** | **15.490** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
