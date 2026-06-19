# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 77.85

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.071 | 0.002 | 0.054 |
| summarize_hop1 | 2.381 | 2.154 | 3.869 |
| query_hop2 | 1.002 | 0.968 | 1.319 |
| retrieve_hop2 | 0.453 | 0.002 | 1.651 |
| summarize_hop2 | 2.300 | 2.136 | 3.756 |
| answer | 1.005 | 0.960 | 1.473 |
| **Total** | **7.213** | **6.741** | **10.967** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
