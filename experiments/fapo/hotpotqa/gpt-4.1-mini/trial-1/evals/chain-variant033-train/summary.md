# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 82.19

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.015 |
| summarize_hop1 | 4.035 | 3.538 | 7.496 |
| query_hop2 | 2.061 | 1.828 | 3.110 |
| retrieve_hop2 | 0.383 | 0.002 | 1.607 |
| summarize_hop2 | 2.892 | 2.607 | 4.608 |
| answer | 1.854 | 1.664 | 2.981 |
| **Total** | **11.264** | **10.707** | **17.703** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
