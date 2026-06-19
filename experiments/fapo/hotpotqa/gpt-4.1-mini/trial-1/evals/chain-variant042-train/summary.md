# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.00

## Score Breakdown
- exact_match: 76.00
- f1: 82.66

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.074 | 0.002 | 0.052 |
| summarize_hop1 | 3.277 | 2.833 | 6.613 |
| query_hop2 | 2.245 | 1.993 | 3.788 |
| retrieve_hop2 | 0.319 | 0.002 | 1.323 |
| summarize_hop2 | 4.036 | 3.606 | 6.858 |
| answer | 2.260 | 2.044 | 4.220 |
| **Total** | **12.212** | **11.659** | **19.876** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 36 |
