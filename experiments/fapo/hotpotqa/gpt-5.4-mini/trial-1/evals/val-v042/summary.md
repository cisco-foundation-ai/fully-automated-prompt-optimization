# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 78.12

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.110 | 0.002 | 0.111 |
| summarize_hop1 | 1.389 | 1.293 | 2.057 |
| query_hop2 | 1.159 | 1.079 | 1.737 |
| retrieve_hop2 | 0.418 | 0.002 | 1.627 |
| summarize_hop2 | 1.633 | 1.545 | 2.323 |
| answer | 0.812 | 0.764 | 1.215 |
| **Total** | **5.521** | **5.079** | **8.015** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
