# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- exact_match: 60.67
- f1: 70.09

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.008 |
| summarize_hop1 | 2.247 | 2.062 | 3.582 |
| query_hop2 | 1.029 | 0.998 | 1.439 |
| retrieve_hop2 | 1.531 | 1.534 | 1.634 |
| summarize_hop2 | 3.713 | 3.585 | 5.737 |
| answer | 1.107 | 1.014 | 1.803 |
| **Total** | **9.630** | **9.268** | **12.948** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
