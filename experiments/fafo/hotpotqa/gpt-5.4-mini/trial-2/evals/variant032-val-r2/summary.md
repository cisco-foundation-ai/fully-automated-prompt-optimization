# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 77.55

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.009 |
| summarize_hop1 | 2.335 | 2.199 | 3.415 |
| query_hop2 | 1.296 | 1.136 | 1.895 |
| retrieve_hop2 | 0.414 | 0.002 | 1.565 |
| summarize_hop2 | 1.739 | 1.538 | 2.770 |
| answer | 0.875 | 0.806 | 1.246 |
| **Total** | **6.675** | **6.256** | **9.619** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 89 |
