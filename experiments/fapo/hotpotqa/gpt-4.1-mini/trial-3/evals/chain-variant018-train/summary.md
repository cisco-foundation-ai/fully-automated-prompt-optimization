# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.026 |
| summarize_hop1 | 3.517 | 3.300 | 5.438 |
| query_hop2 | 2.041 | 1.919 | 3.235 |
| retrieve_hop2 | 0.660 | 0.089 | 1.682 |
| summarize_hop2 | 4.036 | 3.415 | 7.552 |
| answer | 1.405 | 1.343 | 1.982 |
| **Total** | **11.698** | **10.934** | **19.637** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
