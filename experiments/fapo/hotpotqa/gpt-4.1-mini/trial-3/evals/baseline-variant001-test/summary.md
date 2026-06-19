# Evaluation Summary

Total cases: 300

## Composite Score
- average: 37.00

## Score Breakdown
- exact_match: 37.00
- f1: 52.02

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.004 |
| summarize_hop1 | 4.939 | 3.872 | 8.341 |
| query_hop2 | 3.114 | 2.581 | 6.428 |
| retrieve_hop2 | 1.014 | 1.279 | 1.588 |
| summarize_hop2 | 3.421 | 2.901 | 6.155 |
| answer | 2.968 | 2.428 | 5.974 |
| **Total** | **15.465** | **13.966** | **25.061** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 189 |
