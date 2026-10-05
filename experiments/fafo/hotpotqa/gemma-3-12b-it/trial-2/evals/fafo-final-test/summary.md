# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 70.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.091 | 1.276 | 1.632 |
| summarize_hop1 | 6.556 | 3.972 | 8.020 |
| query_hop2 | 4.118 | 1.474 | 5.332 |
| retrieve_hop2 | 1.377 | 1.446 | 1.590 |
| summarize_hop2 | 5.678 | 3.860 | 8.390 |
| answer | 1.732 | 1.239 | 4.147 |
| **Total** | **20.551** | **13.729** | **35.775** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
