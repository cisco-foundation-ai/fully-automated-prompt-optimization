# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.002 | 0.016 |
| summarize_hop1 | 5.132 | 4.319 | 8.871 |
| query_hop2 | 2.231 | 2.007 | 3.883 |
| retrieve_hop2 | 0.791 | 0.098 | 1.646 |
| summarize_hop2 | 4.187 | 3.894 | 7.227 |
| answer | 1.493 | 1.409 | 2.487 |
| **Total** | **13.858** | **13.059** | **21.169** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
