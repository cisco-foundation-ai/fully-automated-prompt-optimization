# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.33

## Score Breakdown
- exact_match: 59.33
- f1: 68.59

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.012 |
| summarize_hop1 | 2.289 | 2.096 | 3.822 |
| query_hop2 | 1.039 | 0.996 | 1.414 |
| retrieve_hop2 | 0.739 | 0.003 | 1.631 |
| summarize_hop2 | 3.670 | 3.505 | 6.113 |
| answer | 1.132 | 1.068 | 1.737 |
| **Total** | **8.899** | **8.497** | **13.704** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 122 |
