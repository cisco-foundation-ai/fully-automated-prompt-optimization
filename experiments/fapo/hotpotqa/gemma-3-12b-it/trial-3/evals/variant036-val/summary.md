# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.33

## Score Breakdown
- exact_match: 60.33
- f1: 69.02

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.012 |
| summarize_hop1 | 2.060 | 1.850 | 3.639 |
| query_hop2 | 1.012 | 0.976 | 1.366 |
| retrieve_hop2 | 0.571 | 0.003 | 1.627 |
| summarize_hop2 | 3.090 | 2.845 | 5.473 |
| answer | 1.121 | 0.986 | 1.672 |
| **Total** | **7.887** | **7.534** | **11.908** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 119 |
