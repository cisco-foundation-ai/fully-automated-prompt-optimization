# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.40

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.007 |
| summarize_hop1 | 4.800 | 4.389 | 7.948 |
| query_hop2 | 2.424 | 2.228 | 3.746 |
| retrieve_hop2 | 0.585 | 0.003 | 1.461 |
| summarize_hop2 | 4.522 | 4.183 | 7.615 |
| answer | 1.869 | 1.702 | 3.183 |
| **Total** | **14.225** | **13.456** | **20.618** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
