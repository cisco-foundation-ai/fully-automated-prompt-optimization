# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 77.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.007 |
| summarize_hop1 | 3.386 | 2.871 | 6.950 |
| query_hop2 | 2.348 | 2.093 | 4.143 |
| retrieve_hop2 | 0.248 | 0.002 | 1.464 |
| summarize_hop2 | 4.040 | 3.751 | 7.222 |
| answer | 2.484 | 2.074 | 3.905 |
| **Total** | **12.531** | **11.656** | **19.502** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
