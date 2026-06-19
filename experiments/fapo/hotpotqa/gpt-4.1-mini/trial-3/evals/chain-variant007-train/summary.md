# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 79.78

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.011 |
| summarize_hop1 | 3.499 | 3.083 | 5.677 |
| query_hop2 | 1.556 | 1.431 | 2.584 |
| retrieve_hop2 | 1.040 | 1.070 | 1.405 |
| summarize_hop2 | 3.330 | 2.812 | 7.178 |
| answer | 1.328 | 1.243 | 1.933 |
| **Total** | **10.758** | **9.630** | **18.979** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
| query_hop2 | 2 |
