# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.03

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.031 |
| summarize_hop1 | 2.439 | 2.319 | 4.072 |
| query_hop2 | 1.054 | 1.043 | 1.448 |
| retrieve_hop2 | 0.592 | 0.002 | 1.637 |
| summarize_hop2 | 2.324 | 2.162 | 3.504 |
| answer | 1.025 | 0.995 | 1.419 |
| **Total** | **7.475** | **6.940** | **11.456** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
