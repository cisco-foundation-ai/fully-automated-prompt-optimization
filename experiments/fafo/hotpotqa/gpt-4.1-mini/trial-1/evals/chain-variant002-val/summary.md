# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.67

## Score Breakdown
- exact_match: 64.67
- f1: 72.50

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.007 |
| summarize_hop1 | 3.090 | 2.806 | 5.773 |
| query_hop2 | 1.763 | 1.694 | 2.602 |
| retrieve_hop2 | 0.786 | 0.430 | 1.700 |
| summarize_hop2 | 2.644 | 2.378 | 4.316 |
| answer | 1.548 | 1.345 | 2.583 |
| **Total** | **9.858** | **9.475** | **14.237** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 106 |
