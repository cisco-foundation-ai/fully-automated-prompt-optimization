# Evaluation Summary

Total cases: 150

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 67.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.364 | 1.333 | 1.768 |
| summarize_hop1 | 1.779 | 1.663 | 2.844 |
| query_hop2 | 1.035 | 0.984 | 1.499 |
| retrieve_hop2 | 1.324 | 1.531 | 1.702 |
| summarize_hop2 | 1.518 | 1.502 | 2.165 |
| answer | 2.979 | 0.865 | 1.434 |
| **Total** | **9.998** | **7.601** | **11.675** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 56 |
