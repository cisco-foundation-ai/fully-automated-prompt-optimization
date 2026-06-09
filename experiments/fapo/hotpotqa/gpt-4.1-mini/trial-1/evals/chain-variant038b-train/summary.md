# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 80.22

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.050 | 0.002 | 0.027 |
| summarize_hop1 | 4.363 | 3.811 | 8.398 |
| query_hop2 | 2.167 | 1.961 | 3.637 |
| retrieve_hop2 | 0.308 | 0.002 | 1.321 |
| summarize_hop2 | 3.768 | 3.327 | 6.880 |
| answer | 1.964 | 1.765 | 3.095 |
| **Total** | **12.621** | **11.811** | **19.201** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
