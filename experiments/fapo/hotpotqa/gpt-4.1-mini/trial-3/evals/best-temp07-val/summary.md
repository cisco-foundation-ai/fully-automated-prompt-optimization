# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 78.22

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.021 | 0.002 | 0.008 |
| summarize_hop1 | 7.982 | 6.421 | 17.279 |
| query_hop2 | 2.802 | 2.528 | 4.812 |
| retrieve_hop2 | 0.687 | 0.004 | 1.568 |
| summarize_hop2 | 4.914 | 4.497 | 7.991 |
| answer | 2.045 | 1.806 | 3.354 |
| **Total** | **18.451** | **16.727** | **29.594** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
