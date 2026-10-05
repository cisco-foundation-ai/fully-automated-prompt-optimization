# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.33

## Score Breakdown
- exact_match: 64.33
- f1: 71.22

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.008 |
| summarize_hop1 | 2.383 | 2.237 | 3.566 |
| query_hop2 | 1.313 | 1.095 | 1.965 |
| retrieve_hop2 | 0.672 | 0.004 | 1.610 |
| summarize_hop2 | 1.857 | 1.796 | 2.652 |
| answer | 0.954 | 0.849 | 1.478 |
| **Total** | **7.196** | **6.739** | **10.317** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 107 |
