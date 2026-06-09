# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 74.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.010 |
| summarize_hop1 | 2.383 | 2.104 | 3.547 |
| query_hop2 | 1.405 | 1.148 | 2.293 |
| retrieve_hop2 | 0.356 | 0.002 | 1.542 |
| summarize_hop2 | 1.869 | 1.693 | 2.770 |
| answer | 0.997 | 0.871 | 1.527 |
| **Total** | **7.038** | **6.245** | **11.185** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
