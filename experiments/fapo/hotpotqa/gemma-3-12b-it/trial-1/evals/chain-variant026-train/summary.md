# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.66

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.043 | 0.002 | 0.051 |
| summarize_hop1 | 2.363 | 2.293 | 3.831 |
| query_hop2 | 1.022 | 0.994 | 1.366 |
| retrieve_hop2 | 0.587 | 0.003 | 1.593 |
| summarize_hop2 | 2.584 | 2.492 | 4.211 |
| answer | 0.852 | 0.806 | 1.228 |
| **Total** | **7.451** | **7.069** | **11.490** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
