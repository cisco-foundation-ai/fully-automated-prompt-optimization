# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 71.61

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.012 |
| summarize_hop1 | 3.455 | 3.217 | 6.051 |
| query_hop2 | 1.169 | 1.105 | 1.729 |
| retrieve_hop2 | 0.572 | 0.003 | 1.605 |
| summarize_hop2 | 3.328 | 3.038 | 5.678 |
| answer | 1.054 | 0.955 | 1.582 |
| **Total** | **9.599** | **9.095** | **14.784** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
