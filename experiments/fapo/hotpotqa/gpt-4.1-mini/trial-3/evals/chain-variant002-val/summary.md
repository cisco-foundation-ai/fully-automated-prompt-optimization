# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 72.63

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 3.782 | 3.287 | 7.200 |
| query_hop2 | 1.855 | 1.720 | 2.996 |
| retrieve_hop2 | 0.876 | 0.663 | 1.740 |
| summarize_hop2 | 2.797 | 2.560 | 4.699 |
| answer | 1.286 | 1.180 | 1.967 |
| **Total** | **10.598** | **10.017** | **16.234** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 102 |
