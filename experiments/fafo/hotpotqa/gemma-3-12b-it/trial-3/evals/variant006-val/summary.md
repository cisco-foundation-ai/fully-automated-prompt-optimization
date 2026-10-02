# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- exact_match: 58.33
- f1: 67.68

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.010 |
| summarize_hop1 | 1.792 | 1.558 | 3.216 |
| query_hop2 | 1.032 | 0.968 | 1.511 |
| retrieve_hop2 | 0.518 | 0.002 | 1.630 |
| summarize_hop2 | 2.914 | 2.707 | 5.338 |
| answer | 1.136 | 1.027 | 1.957 |
| **Total** | **7.430** | **7.040** | **10.856** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 125 |
