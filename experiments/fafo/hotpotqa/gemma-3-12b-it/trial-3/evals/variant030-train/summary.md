# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 74.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.069 | 0.002 | 0.060 |
| summarize_hop1 | 2.296 | 2.130 | 3.542 |
| query_hop2 | 1.049 | 1.021 | 1.419 |
| retrieve_hop2 | 0.613 | 0.005 | 1.626 |
| summarize_hop2 | 2.361 | 2.228 | 3.586 |
| answer | 1.088 | 1.058 | 1.554 |
| **Total** | **7.476** | **7.091** | **11.056** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
