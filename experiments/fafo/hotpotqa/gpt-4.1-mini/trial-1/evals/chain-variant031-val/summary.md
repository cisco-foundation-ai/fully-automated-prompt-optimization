# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 77.03

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.010 |
| summarize_hop1 | 4.277 | 3.493 | 9.926 |
| query_hop2 | 2.122 | 1.798 | 3.823 |
| retrieve_hop2 | 0.334 | 0.002 | 1.538 |
| summarize_hop2 | 3.311 | 2.966 | 5.639 |
| answer | 1.967 | 1.781 | 3.266 |
| **Total** | **12.025** | **11.130** | **19.726** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
