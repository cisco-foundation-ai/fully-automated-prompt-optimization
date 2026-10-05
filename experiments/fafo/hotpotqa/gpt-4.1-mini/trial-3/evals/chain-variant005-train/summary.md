# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.61

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.008 |
| summarize_hop1 | 3.101 | 2.740 | 5.498 |
| query_hop2 | 1.822 | 1.629 | 2.917 |
| retrieve_hop2 | 0.894 | 0.119 | 1.751 |
| summarize_hop2 | 2.359 | 2.234 | 3.777 |
| answer | 1.358 | 1.252 | 2.289 |
| **Total** | **9.565** | **8.848** | **14.308** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
