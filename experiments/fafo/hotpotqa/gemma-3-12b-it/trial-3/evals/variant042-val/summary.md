# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- exact_match: 60.67
- f1: 70.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.008 |
| summarize_hop1 | 2.321 | 2.182 | 3.816 |
| query_hop2 | 1.092 | 1.058 | 1.494 |
| retrieve_hop2 | 1.296 | 1.314 | 1.592 |
| summarize_hop2 | 3.393 | 3.311 | 5.374 |
| answer | 1.134 | 1.085 | 1.714 |
| **Total** | **9.240** | **8.858** | **13.394** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
