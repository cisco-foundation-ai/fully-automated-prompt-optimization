# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.68

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.007 |
| summarize_hop1 | 1.586 | 1.469 | 2.606 |
| query_hop2 | 1.099 | 1.046 | 1.547 |
| retrieve_hop2 | 0.912 | 1.067 | 1.681 |
| summarize_hop2 | 1.606 | 1.491 | 2.370 |
| answer | 0.861 | 0.796 | 1.267 |
| **Total** | **6.092** | **5.883** | **8.251** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
