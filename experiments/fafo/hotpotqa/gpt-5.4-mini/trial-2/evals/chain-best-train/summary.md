# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.40

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.013 |
| summarize_hop1 | 2.372 | 2.233 | 3.791 |
| query_hop2 | 1.267 | 1.149 | 2.392 |
| retrieve_hop2 | 0.594 | 0.002 | 1.392 |
| summarize_hop2 | 1.905 | 1.709 | 2.976 |
| answer | 1.003 | 0.870 | 1.487 |
| **Total** | **7.163** | **6.457** | **10.649** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
