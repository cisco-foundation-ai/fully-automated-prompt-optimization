# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.00

## Score Breakdown
- exact_match: 59.00
- f1: 66.77

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.008 |
| summarize_hop1 | 1.734 | 1.542 | 3.144 |
| query_hop2 | 0.968 | 0.913 | 1.334 |
| retrieve_hop2 | 0.980 | 0.854 | 1.667 |
| summarize_hop2 | 2.706 | 2.663 | 4.259 |
| answer | 1.026 | 0.975 | 1.484 |
| **Total** | **7.431** | **7.268** | **10.689** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 123 |
