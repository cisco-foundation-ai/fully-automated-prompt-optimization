# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 81.06

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.048 |
| summarize_hop1 | 5.042 | 3.736 | 10.447 |
| query_hop2 | 1.905 | 1.688 | 3.352 |
| retrieve_hop2 | 0.386 | 0.002 | 1.527 |
| summarize_hop2 | 3.408 | 2.975 | 6.808 |
| answer | 1.896 | 1.629 | 3.006 |
| **Total** | **12.678** | **11.100** | **20.759** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
