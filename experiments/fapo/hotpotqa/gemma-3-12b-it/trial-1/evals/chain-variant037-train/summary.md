# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.16

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.013 |
| summarize_hop1 | 2.673 | 2.408 | 5.027 |
| query_hop2 | 1.343 | 1.332 | 1.858 |
| retrieve_hop2 | 0.597 | 0.002 | 1.370 |
| summarize_hop2 | 2.243 | 2.131 | 3.396 |
| answer | 0.957 | 0.912 | 1.370 |
| **Total** | **7.845** | **7.242** | **11.679** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
