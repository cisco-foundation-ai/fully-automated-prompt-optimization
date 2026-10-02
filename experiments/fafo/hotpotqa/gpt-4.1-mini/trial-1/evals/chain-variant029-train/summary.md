# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 81.17

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.046 | 0.002 | 0.053 |
| summarize_hop1 | 3.197 | 2.835 | 5.645 |
| query_hop2 | 1.607 | 1.430 | 2.641 |
| retrieve_hop2 | 0.311 | 0.004 | 1.108 |
| summarize_hop2 | 3.315 | 3.057 | 5.664 |
| answer | 1.860 | 1.689 | 3.077 |
| **Total** | **10.337** | **9.502** | **15.680** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
