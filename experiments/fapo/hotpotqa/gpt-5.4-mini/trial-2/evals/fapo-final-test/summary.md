# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.052 | 1.089 | 1.702 |
| summarize_hop1 | 2.198 | 2.077 | 3.308 |
| query_hop2 | 1.250 | 1.111 | 1.747 |
| retrieve_hop2 | 1.251 | 1.319 | 1.629 |
| summarize_hop2 | 1.713 | 1.583 | 2.324 |
| answer | 0.944 | 0.869 | 1.577 |
| **Total** | **8.407** | **8.042** | **10.851** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
