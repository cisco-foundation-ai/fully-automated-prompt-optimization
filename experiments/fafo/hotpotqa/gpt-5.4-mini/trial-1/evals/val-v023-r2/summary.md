# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 77.50

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.113 | 0.002 | 0.117 |
| summarize_hop1 | 1.292 | 1.191 | 1.891 |
| query_hop2 | 1.040 | 0.983 | 1.398 |
| retrieve_hop2 | 0.469 | 0.002 | 1.638 |
| summarize_hop2 | 1.484 | 1.405 | 2.170 |
| answer | 0.770 | 0.730 | 1.113 |
| **Total** | **5.169** | **4.535** | **7.652** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
