# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.33

## Score Breakdown
- exact_match: 61.33
- f1: 70.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.003 | 0.012 |
| summarize_hop1 | 2.365 | 2.240 | 3.783 |
| query_hop2 | 1.090 | 1.030 | 1.519 |
| retrieve_hop2 | 0.444 | 0.005 | 1.579 |
| summarize_hop2 | 3.398 | 3.260 | 5.723 |
| answer | 1.150 | 1.081 | 1.932 |
| **Total** | **8.480** | **8.115** | **12.685** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 116 |
