# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- exact_match: 73.00
- f1: 79.59

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 4.342 | 3.812 | 7.768 |
| query_hop2 | 2.645 | 2.409 | 4.348 |
| retrieve_hop2 | 1.558 | 1.512 | 1.623 |
| summarize_hop2 | 4.943 | 4.550 | 8.468 |
| answer | 1.974 | 1.652 | 4.239 |
| **Total** | **15.464** | **14.647** | **22.667** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 81 |
