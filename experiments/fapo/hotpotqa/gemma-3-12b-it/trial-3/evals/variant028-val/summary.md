# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.67

## Score Breakdown
- exact_match: 61.67
- f1: 69.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.003 | 0.011 |
| summarize_hop1 | 2.239 | 2.063 | 3.604 |
| query_hop2 | 1.012 | 0.977 | 1.425 |
| retrieve_hop2 | 0.642 | 0.005 | 1.603 |
| summarize_hop2 | 3.533 | 3.413 | 5.533 |
| answer | 1.115 | 1.048 | 1.716 |
| **Total** | **8.567** | **8.091** | **12.341** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 115 |
