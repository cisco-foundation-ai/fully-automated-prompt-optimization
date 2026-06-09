# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.33

## Score Breakdown
- exact_match: 62.33
- f1: 70.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.010 |
| summarize_hop1 | 2.486 | 2.243 | 4.178 |
| query_hop2 | 1.415 | 1.363 | 2.101 |
| retrieve_hop2 | 0.831 | 0.010 | 1.654 |
| summarize_hop2 | 1.937 | 1.832 | 2.965 |
| answer | 1.074 | 1.046 | 1.540 |
| **Total** | **7.758** | **7.394** | **11.295** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 113 |
