# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.38

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.020 |
| summarize_hop1 | 4.004 | 3.427 | 7.205 |
| query_hop2 | 1.893 | 1.665 | 3.391 |
| retrieve_hop2 | 0.931 | 0.241 | 1.759 |
| summarize_hop2 | 2.506 | 2.341 | 3.833 |
| answer | 1.191 | 1.125 | 1.877 |
| **Total** | **10.554** | **9.840** | **16.139** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
