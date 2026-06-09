# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.10

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.059 | 0.002 | 0.024 |
| summarize_hop1 | 3.239 | 2.745 | 6.188 |
| query_hop2 | 1.598 | 1.490 | 2.424 |
| retrieve_hop2 | 0.632 | 0.079 | 1.689 |
| summarize_hop2 | 2.962 | 2.745 | 4.618 |
| answer | 1.292 | 1.158 | 1.922 |
| **Total** | **9.783** | **8.896** | **15.365** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
