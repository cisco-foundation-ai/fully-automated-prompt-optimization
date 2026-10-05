# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.015 |
| summarize_hop1 | 2.072 | 1.758 | 3.928 |
| query_hop2 | 1.029 | 0.948 | 1.295 |
| retrieve_hop2 | 0.897 | 0.003 | 1.695 |
| summarize_hop2 | 2.756 | 2.692 | 4.308 |
| answer | 1.067 | 0.983 | 1.661 |
| **Total** | **7.847** | **7.155** | **12.374** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
