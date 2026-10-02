# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.064 | 0.002 | 0.097 |
| summarize_hop1 | 1.381 | 1.264 | 2.286 |
| query_hop2 | 1.131 | 1.067 | 1.660 |
| retrieve_hop2 | 0.647 | 0.002 | 1.720 |
| summarize_hop2 | 1.733 | 1.629 | 2.700 |
| answer | 0.839 | 0.730 | 1.418 |
| **Total** | **5.796** | **5.124** | **8.936** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
| query_hop2 | 1 |
