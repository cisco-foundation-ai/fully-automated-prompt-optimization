# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 75.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.010 |
| summarize_hop1 | 4.606 | 4.143 | 8.730 |
| query_hop2 | 2.100 | 1.942 | 3.739 |
| retrieve_hop2 | 0.980 | 1.082 | 1.655 |
| summarize_hop2 | 4.362 | 3.962 | 7.822 |
| answer | 2.525 | 2.054 | 5.501 |
| **Total** | **14.590** | **13.738** | **22.729** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
