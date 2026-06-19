# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 73.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.008 |
| summarize_hop1 | 2.297 | 2.170 | 3.307 |
| query_hop2 | 1.249 | 1.147 | 1.751 |
| retrieve_hop2 | 0.356 | 0.002 | 1.527 |
| summarize_hop2 | 1.510 | 1.441 | 2.067 |
| answer | 0.846 | 0.812 | 1.298 |
| **Total** | **6.291** | **5.857** | **8.641** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
