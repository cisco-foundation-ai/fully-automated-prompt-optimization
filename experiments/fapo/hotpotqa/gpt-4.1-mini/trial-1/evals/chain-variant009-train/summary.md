# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.30

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.026 |
| summarize_hop1 | 4.067 | 3.461 | 7.222 |
| query_hop2 | 1.922 | 1.822 | 2.904 |
| retrieve_hop2 | 0.715 | 0.097 | 1.741 |
| summarize_hop2 | 3.655 | 3.212 | 7.252 |
| answer | 1.632 | 1.510 | 2.611 |
| **Total** | **12.030** | **10.943** | **18.069** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
