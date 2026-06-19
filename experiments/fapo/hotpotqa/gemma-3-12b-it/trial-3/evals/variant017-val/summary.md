# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.33

## Score Breakdown
- exact_match: 60.33
- f1: 68.83

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.002 | 0.011 |
| summarize_hop1 | 1.983 | 1.875 | 3.298 |
| query_hop2 | 1.054 | 1.015 | 1.495 |
| retrieve_hop2 | 0.709 | 0.007 | 1.626 |
| summarize_hop2 | 3.383 | 3.261 | 5.220 |
| answer | 1.438 | 1.344 | 2.127 |
| **Total** | **8.589** | **8.427** | **12.129** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 119 |
