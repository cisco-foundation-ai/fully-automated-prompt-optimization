# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.67

## Score Breakdown
- exact_match: 59.67
- f1: 68.43

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.010 |
| summarize_hop1 | 2.223 | 2.075 | 3.623 |
| query_hop2 | 1.059 | 1.017 | 1.465 |
| retrieve_hop2 | 1.002 | 1.106 | 1.350 |
| summarize_hop2 | 3.313 | 3.080 | 5.392 |
| answer | 1.119 | 1.071 | 1.732 |
| **Total** | **8.741** | **8.261** | **12.373** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 121 |
