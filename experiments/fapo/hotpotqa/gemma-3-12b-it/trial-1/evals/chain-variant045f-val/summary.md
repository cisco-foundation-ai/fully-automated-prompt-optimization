# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.67

## Score Breakdown
- exact_match: 63.67
- f1: 71.50

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.009 |
| summarize_hop1 | 2.348 | 2.191 | 4.092 |
| query_hop2 | 1.090 | 1.019 | 1.547 |
| retrieve_hop2 | 0.434 | 0.002 | 1.601 |
| summarize_hop2 | 2.534 | 2.499 | 3.702 |
| answer | 1.042 | 1.002 | 1.519 |
| **Total** | **7.480** | **6.965** | **10.880** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 109 |
