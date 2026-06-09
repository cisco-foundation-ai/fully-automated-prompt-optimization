# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.50

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.046 | 0.002 | 0.040 |
| summarize_hop1 | 3.534 | 3.067 | 6.033 |
| query_hop2 | 1.543 | 1.357 | 2.363 |
| retrieve_hop2 | 0.350 | 0.002 | 1.483 |
| summarize_hop2 | 3.183 | 2.964 | 4.499 |
| answer | 1.663 | 1.522 | 3.004 |
| **Total** | **10.319** | **9.753** | **15.504** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
