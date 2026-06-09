# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.018 |
| summarize_hop1 | 3.285 | 3.226 | 5.051 |
| query_hop2 | 1.184 | 1.119 | 1.724 |
| retrieve_hop2 | 0.574 | 0.002 | 1.598 |
| summarize_hop2 | 3.130 | 3.017 | 4.923 |
| answer | 1.046 | 0.973 | 1.658 |
| **Total** | **9.254** | **8.806** | **13.049** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
