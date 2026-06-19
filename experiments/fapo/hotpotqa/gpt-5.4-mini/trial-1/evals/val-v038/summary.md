# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 78.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.081 | 0.002 | 0.106 |
| summarize_hop1 | 1.421 | 1.319 | 2.297 |
| query_hop2 | 1.133 | 1.064 | 1.707 |
| retrieve_hop2 | 0.856 | 0.006 | 1.662 |
| summarize_hop2 | 1.617 | 1.527 | 2.343 |
| answer | 0.859 | 0.731 | 1.219 |
| **Total** | **5.967** | **5.502** | **8.882** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
