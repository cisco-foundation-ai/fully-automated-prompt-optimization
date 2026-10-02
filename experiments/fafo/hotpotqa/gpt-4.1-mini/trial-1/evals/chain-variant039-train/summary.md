# Evaluation Summary

Total cases: 150

## Composite Score
- average: 79.33

## Score Breakdown
- exact_match: 79.33
- f1: 84.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.049 | 0.003 | 0.054 |
| summarize_hop1 | 4.417 | 3.779 | 8.730 |
| query_hop2 | 2.068 | 1.836 | 3.311 |
| retrieve_hop2 | 0.293 | 0.002 | 1.144 |
| summarize_hop2 | 3.898 | 3.344 | 6.954 |
| answer | 2.072 | 1.843 | 3.492 |
| **Total** | **12.797** | **11.735** | **21.503** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 31 |
