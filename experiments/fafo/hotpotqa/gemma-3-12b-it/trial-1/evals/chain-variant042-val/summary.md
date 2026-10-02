# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.67

## Score Breakdown
- exact_match: 61.67
- f1: 69.76

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.012 |
| summarize_hop1 | 2.319 | 2.154 | 3.756 |
| query_hop2 | 1.074 | 1.007 | 1.545 |
| retrieve_hop2 | 0.514 | 0.002 | 1.598 |
| summarize_hop2 | 2.661 | 2.577 | 3.724 |
| answer | 1.056 | 0.976 | 1.665 |
| **Total** | **7.653** | **7.484** | **11.012** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 115 |
