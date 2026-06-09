# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 80.25

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.047 | 0.002 | 0.016 |
| summarize_hop1 | 2.007 | 1.778 | 3.462 |
| query_hop2 | 1.055 | 0.998 | 1.546 |
| retrieve_hop2 | 0.538 | 0.002 | 1.106 |
| summarize_hop2 | 3.100 | 3.046 | 4.462 |
| answer | 1.161 | 1.068 | 1.692 |
| **Total** | **7.908** | **7.325** | **12.655** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
