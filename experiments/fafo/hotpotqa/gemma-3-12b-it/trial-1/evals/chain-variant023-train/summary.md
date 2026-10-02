# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 74.56

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.069 | 0.003 | 0.043 |
| summarize_hop1 | 2.432 | 2.178 | 4.223 |
| query_hop2 | 1.297 | 1.246 | 1.827 |
| retrieve_hop2 | 0.464 | 0.003 | 1.568 |
| summarize_hop2 | 2.283 | 2.186 | 3.681 |
| answer | 1.119 | 1.069 | 1.607 |
| **Total** | **7.663** | **7.332** | **11.046** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
