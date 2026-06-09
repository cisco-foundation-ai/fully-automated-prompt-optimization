# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.00

## Score Breakdown
- exact_match: 76.00
- f1: 81.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.008 |
| summarize_hop1 | 6.082 | 5.210 | 11.512 |
| query_hop2 | 2.905 | 2.747 | 4.562 |
| retrieve_hop2 | 1.546 | 1.306 | 1.594 |
| summarize_hop2 | 5.032 | 4.716 | 8.671 |
| answer | 2.275 | 2.048 | 3.960 |
| **Total** | **17.844** | **16.680** | **28.820** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 36 |
