# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.003 | 0.021 |
| summarize_hop1 | 2.099 | 2.024 | 3.245 |
| query_hop2 | 1.124 | 1.031 | 1.762 |
| retrieve_hop2 | 0.767 | 0.003 | 1.670 |
| summarize_hop2 | 1.781 | 1.627 | 2.675 |
| answer | 0.835 | 0.796 | 1.193 |
| **Total** | **6.649** | **6.038** | **9.597** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
