# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 75.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.047 | 0.002 | 0.008 |
| summarize_hop1 | 2.665 | 2.308 | 3.857 |
| query_hop2 | 1.490 | 1.212 | 1.989 |
| retrieve_hop2 | 0.346 | 0.002 | 1.497 |
| summarize_hop2 | 1.803 | 1.625 | 2.654 |
| answer | 1.011 | 0.841 | 1.971 |
| **Total** | **7.362** | **6.516** | **11.417** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
