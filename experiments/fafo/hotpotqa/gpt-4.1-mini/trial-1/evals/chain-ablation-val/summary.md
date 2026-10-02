# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 73.85

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.008 |
| summarize_hop1 | 3.130 | 2.751 | 5.822 |
| query_hop2 | 2.030 | 1.702 | 2.744 |
| retrieve_hop2 | 0.779 | 0.391 | 1.643 |
| summarize_hop2 | 2.654 | 2.498 | 3.958 |
| answer | 1.569 | 1.396 | 2.687 |
| **Total** | **10.178** | **9.314** | **14.421** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 100 |
