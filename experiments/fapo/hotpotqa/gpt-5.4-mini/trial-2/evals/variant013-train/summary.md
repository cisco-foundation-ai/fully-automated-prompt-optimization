# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.00

## Score Breakdown
- exact_match: 76.00
- f1: 80.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.083 | 0.002 | 0.064 |
| summarize_hop1 | 2.090 | 1.994 | 3.017 |
| query_hop2 | 1.108 | 1.063 | 1.630 |
| retrieve_hop2 | 0.601 | 0.002 | 1.650 |
| summarize_hop2 | 1.659 | 1.611 | 2.451 |
| answer | 0.825 | 0.774 | 1.108 |
| **Total** | **6.365** | **5.892** | **9.114** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 36 |
