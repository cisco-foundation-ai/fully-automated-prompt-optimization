# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.002 | 0.034 |
| summarize_hop1 | 5.024 | 4.458 | 8.944 |
| query_hop2 | 2.750 | 2.535 | 5.111 |
| retrieve_hop2 | 0.680 | 0.072 | 1.629 |
| summarize_hop2 | 5.423 | 4.770 | 9.154 |
| answer | 2.011 | 1.773 | 3.317 |
| **Total** | **15.919** | **14.730** | **25.655** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
