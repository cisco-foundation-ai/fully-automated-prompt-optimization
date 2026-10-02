# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 80.69

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.012 |
| summarize_hop1 | 4.348 | 3.670 | 8.444 |
| query_hop2 | 1.905 | 1.782 | 2.899 |
| retrieve_hop2 | 0.662 | 0.067 | 1.623 |
| summarize_hop2 | 4.702 | 4.316 | 8.519 |
| answer | 2.975 | 2.278 | 7.616 |
| **Total** | **14.619** | **13.814** | **24.982** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
