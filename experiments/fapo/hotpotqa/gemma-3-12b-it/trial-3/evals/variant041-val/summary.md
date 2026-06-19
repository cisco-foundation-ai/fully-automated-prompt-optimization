# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.33

## Score Breakdown
- exact_match: 57.33
- f1: 66.66

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.012 |
| summarize_hop1 | 2.324 | 2.125 | 3.752 |
| query_hop2 | 1.085 | 1.034 | 1.514 |
| retrieve_hop2 | 0.538 | 0.002 | 1.626 |
| summarize_hop2 | 3.352 | 3.181 | 5.765 |
| answer | 1.228 | 1.147 | 1.882 |
| **Total** | **8.547** | **7.998** | **12.720** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 128 |
