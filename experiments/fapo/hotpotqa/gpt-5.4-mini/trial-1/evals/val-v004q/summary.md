# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 72.62

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.048 | 0.002 | 0.011 |
| summarize_hop1 | 1.173 | 1.089 | 1.810 |
| query_hop2 | 1.102 | 1.034 | 1.663 |
| retrieve_hop2 | 1.224 | 1.077 | 1.666 |
| summarize_hop2 | 1.092 | 1.030 | 1.500 |
| answer | 0.851 | 0.809 | 1.279 |
| **Total** | **5.491** | **5.120** | **7.378** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
