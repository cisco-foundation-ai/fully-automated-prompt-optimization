# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.42

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.059 | 0.004 | 0.050 |
| summarize_hop1 | 2.385 | 2.311 | 3.892 |
| query_hop2 | 0.994 | 0.946 | 1.387 |
| retrieve_hop2 | 0.448 | 0.007 | 1.137 |
| summarize_hop2 | 2.520 | 2.434 | 3.768 |
| answer | 1.010 | 0.940 | 1.568 |
| **Total** | **7.416** | **6.950** | **10.679** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
