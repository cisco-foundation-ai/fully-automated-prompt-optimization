# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.58

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.003 | 0.011 |
| summarize_hop1 | 4.349 | 3.708 | 8.395 |
| query_hop2 | 2.116 | 1.792 | 4.026 |
| retrieve_hop2 | 0.295 | 0.002 | 1.540 |
| summarize_hop2 | 3.442 | 3.045 | 5.988 |
| answer | 2.063 | 1.771 | 3.550 |
| **Total** | **12.296** | **11.521** | **19.004** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
