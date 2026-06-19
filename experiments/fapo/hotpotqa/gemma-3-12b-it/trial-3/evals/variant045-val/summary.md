# Evaluation Summary

Total cases: 300

## Composite Score
- average: 56.00

## Score Breakdown
- exact_match: 56.00
- f1: 64.63

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.012 |
| summarize_hop1 | 2.299 | 2.151 | 3.752 |
| query_hop2 | 1.079 | 1.030 | 1.442 |
| retrieve_hop2 | 0.504 | 0.002 | 1.605 |
| summarize_hop2 | 3.438 | 3.306 | 5.734 |
| answer | 1.119 | 1.070 | 1.688 |
| **Total** | **8.470** | **8.093** | **13.015** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 132 |
