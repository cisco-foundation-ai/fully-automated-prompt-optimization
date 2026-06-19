# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.009 |
| summarize_hop1 | 2.427 | 2.260 | 3.634 |
| query_hop2 | 1.341 | 1.172 | 2.158 |
| retrieve_hop2 | 0.475 | 0.002 | 1.635 |
| summarize_hop2 | 1.799 | 1.528 | 2.514 |
| answer | 0.965 | 0.837 | 1.465 |
| **Total** | **7.025** | **6.364** | **10.346** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
