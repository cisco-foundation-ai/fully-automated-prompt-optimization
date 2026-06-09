# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.56

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.002 | 0.030 |
| summarize_hop1 | 3.445 | 3.199 | 6.263 |
| query_hop2 | 2.436 | 2.002 | 4.389 |
| retrieve_hop2 | 0.606 | 0.002 | 1.594 |
| summarize_hop2 | 4.049 | 3.595 | 6.729 |
| answer | 2.085 | 1.917 | 3.627 |
| **Total** | **12.652** | **11.594** | **18.715** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
