# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.16

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.150 | 0.002 | 0.113 |
| summarize_hop1 | 1.404 | 1.320 | 2.098 |
| query_hop2 | 1.161 | 1.076 | 1.777 |
| retrieve_hop2 | 0.578 | 0.002 | 1.638 |
| summarize_hop2 | 1.658 | 1.551 | 2.499 |
| answer | 0.782 | 0.738 | 1.097 |
| **Total** | **5.732** | **5.169** | **8.187** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
| query_hop2 | 2 |
