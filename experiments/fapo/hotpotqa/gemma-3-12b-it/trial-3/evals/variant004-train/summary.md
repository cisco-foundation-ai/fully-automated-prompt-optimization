# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 72.40

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.087 | 0.002 | 0.070 |
| summarize_hop1 | 2.278 | 2.144 | 3.811 |
| query_hop2 | 0.957 | 0.935 | 1.314 |
| retrieve_hop2 | 1.175 | 1.452 | 1.719 |
| summarize_hop2 | 2.685 | 2.545 | 4.196 |
| answer | 1.054 | 0.970 | 1.558 |
| **Total** | **8.235** | **7.918** | **11.809** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
