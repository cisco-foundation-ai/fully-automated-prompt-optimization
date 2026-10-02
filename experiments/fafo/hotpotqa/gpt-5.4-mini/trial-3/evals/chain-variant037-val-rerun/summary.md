# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- exact_match: 73.00
- f1: 80.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.059 | 0.002 | 0.011 |
| summarize_hop1 | 1.257 | 1.213 | 1.869 |
| query_hop2 | 1.055 | 0.994 | 1.514 |
| retrieve_hop2 | 0.316 | 0.002 | 1.542 |
| summarize_hop2 | 1.308 | 1.238 | 1.813 |
| answer | 0.955 | 0.903 | 1.279 |
| **Total** | **4.950** | **4.625** | **7.054** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 81 |
