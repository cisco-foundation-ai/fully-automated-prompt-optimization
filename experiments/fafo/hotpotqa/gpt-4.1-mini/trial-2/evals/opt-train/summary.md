# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.67

## Score Breakdown
- exact_match: 76.67
- f1: 83.38

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.060 | 0.002 | 0.026 |
| summarize_hop1 | 3.104 | 2.738 | 5.476 |
| query_hop2 | 1.455 | 1.328 | 2.375 |
| retrieve_hop2 | 0.504 | 0.002 | 1.582 |
| summarize_hop2 | 3.120 | 2.806 | 5.697 |
| answer | 1.162 | 1.066 | 1.581 |
| **Total** | **9.404** | **8.793** | **15.790** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 35 |
