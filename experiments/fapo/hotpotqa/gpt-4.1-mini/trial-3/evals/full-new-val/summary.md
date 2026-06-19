# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 75.81

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.008 |
| summarize_hop1 | 5.706 | 4.953 | 11.550 |
| query_hop2 | 3.727 | 3.110 | 7.588 |
| retrieve_hop2 | 1.196 | 1.517 | 1.626 |
| summarize_hop2 | 4.969 | 4.386 | 9.762 |
| answer | 2.148 | 1.851 | 3.712 |
| **Total** | **17.764** | **16.105** | **28.588** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
